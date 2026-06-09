# Plan de Remediación y Verificación — TravelHub

## Diagnóstico resumido

Tras analizar 671 tests (14 bookings + 57 finance + ~600 core), el stack completo de Celery,
la configuración de base de datos, los rate-limiters, y 13 management commands:

### Fortalezas reales
- `select_for_update()` usado correctamente en facturación, webhooks, pagos y transacciones
- `CONN_MAX_AGE = 600` + `CONN_HEALTH_CHECKS = True` configurados
- `cache.add()` (SETNX) usado para idempotencia de tasks Celery
- Compound indexes bien diseñados en `Venta`, `Factura`, `BoletoImportado`
- `GinIndex` en `datos_parseados` para búsquedas JSON
- `django-axes` bloqueando por username/IP

### Problemas reales encontrados

| # | Severidad | Problema | Impacto |
|---|-----------|----------|---------|
| 1 | **CRÍTICO** | `.env` con DB password en texto plano (`travelhub2026`) | Filtración de credenciales si el repo se compromete |
| 2 | **CRÍTICO** | 6 rate-limiters con `cache.get`+`cache.set` no atómicos | Race condition: conteos incorrectos, bypass de rate-limit |
| 3 | **CRÍTICO** | Sin PgBouncer/connection pooling en PostgreSQL | Conexiones se caen bajo pico (50+ workers Celery) |
| 4 | **CRÍTICO** | `SECRET_KEY` hardcodeada en `.env` sin fallback | App no arranca si falta env var; sin rotación |
| 5 | **ALTO** | 13+ N+1 queries en views, tasks, signals, commands | DB hace +10 queries extra por cada request/loop |
| 6 | **ALTO** | 9 management commands cargan tablas completas en memoria | `list(Agencia.objects.all())`, `list(Pais.objects.all())` — OOM si la tabla crece |
| 7 | **ALTO** | Missing indexes en `Pago`, `FeeVenta`, `VentaAuditFinding`, `FacturaFiscal` | Full scans en tablas que crecen 100k+ filas |
| 8 | **ALTO** | Tasks Celery sin `transaction.on_commit()` en señales | Tareas procesan datos que nunca se persistieron |
| 9 | **MEDIO** | Señales sincrónicas hacen recálculos pesados + HTTP | Requests bloquean usuarios mientras se recalculan finanzas |
| 10 | **MEDIO** | No hay chunking/paginación en iteraciones de tasks | Una agencia con 50k ventas puede matar el worker |
| 11 | **BAJO** | `test_api_requires_authentication` falla (namespace `api` no existe) | La suite no es 100% verde |
| 12 | **BAJO** | Test `test_security_headers` falla por Axes (sin request mock) | Seguridad de headers no se verifica |

---

## Fase 1: Seguridad y Estabilidad (Días 1-2)

### 1.1 Rotar credenciales y mover a vault
- Generar nuevo `SECRET_KEY` (64 bytes hex)
- Mover `DB_PASSWORD` a variable de entorno del sistema / secrets manager
- Eliminar `.env` del repo (agregar a `.gitignore` raíz)
- Hacer que `settings.py`:

### 1.2 Arreglar rate-limiters atómicos
- `core/middleware_saas.py:27` — cambiar `cache.get`+`cache.set` → `cache.incr()`
- `core/middleware.py:332` — lo mismo
- `core/views/public_views.py:29` — lo mismo
- `core/views/auth_views.py:51-88` — lo mismo (múltiples instancias)
- `core/views/onboarding_views.py:25` — lo mismo
- `core/views/god_mode_views.py:152,177` — lo mismo
- `core/middleware_ai_ratelimit.py:51` — usar `cache.add` en vez de `cache.set`

### 1.3 Agregar PgBouncer
- Crear `docker-compose.override.yml` con servicio `pgbouncer`
- Configurar pool de 20 conexiones, `server_idle_timeout=600`
- Apuntar Django a `pgbouncer:6432` en vez de directo a PostgreSQL
- Configurar `CONN_MAX_AGE = 0` (PgBouncer maneja pooling, no Django)

### 1.4 Fix test de seguridad rotos
- `tests/test_security.py:44`: arreglar URL o marcar skip con condición
- `tests/test_security_headers.py`: mock `request` para Axes

**Criterio de éxito:** 0 tests rotos en security suite, rate-limiters verificados con 2 requests concurrentes.

---

## Fase 2: Performance de Base de Datos (Días 3-5)

### 2.1 Eliminar N+1 queries
Por cada archivo listado en el diagnóstico:
- Agregar `.select_related()` y `.prefetch_related()` en las queries del loop
- O refactorizar el loop para usar una sola query con JOIN

Prioridad:
1. `apps/bookings/bookings_views.py:122,136` — vistas que se sirven en cada request de venta
2. `apps/bookings/services/automation.py:255` — automation loop
3. `apps/finance/services/facturacion_service.py:145,272` — facturación de todas las ventas
4. `apps/finance/services/commission_service.py:48` — loop de comisiones
5. `core/permissions.py:22` — middleware que se ejecuta en cada request
6. `core/views/reportes_views.py:79,297` — reportes batch

### 2.2 Agregar missing indexes
Migration con `RunSQL` o `AddIndex`:
- `Pago.creado` — `db_index=True`
- `FeeVenta.creado` — `db_index=True`
- `VentaAuditFinding` — índice compuesto en `(venta, estado, fecha_deteccion)`
- `FacturaFiscal` — índice en `(venta_id, estado_fiscal)`
- `Venta.localizador` — índice para lookup exacto (no `icontains`)

### 2.3 Paginar management commands
- `core/management/commands/warmup_cache.py` — .iterator() en vez de list()
- `apps/finance/tasks.py:148` — .iterator() + .only() para evitar cargar todo el modelo
- `apps/bookings/tasks.py:224,306` — .iterator() en vez de list()

**Criterio de éxito:** Management commands con `.iterator()`, N+1 eliminado de los 10 archivos priorizados, migraciones de índices aplicadas sin errores.

---

## Fase 3: Celery y Async (Días 6-7)

### 3.1 transaction.on_commit para señales
- `apps/bookings/signals.py:73` — envolver `.delay()` en `transaction.on_commit()`
- `apps/finance/signals.py:25` — envolver `.delay()` en `transaction.on_commit()`
- `core/signals.py:110` — NOTA: señales que hacen HTTP deben delegar a Celery primero

### 3.2 Mover llamadas HTTP sincrónicas a Celery
- `core/signals.py:116-124` (`send_to_telegram_if_needed`, `send_to_whatsapp_if_needed`) → crear tasks y llamar con `.delay()`
- `apps/bookings/signals.py:150` (`dispatch_post_save_actions`) → mover a task
- `apps/bookings/signals.py:168` (`audit_venta`) → mover a task

### 3.3 Chunking en tasks batch
- `apps/finance/tasks_settlements.py:40` — procesar agencias en lotes de 50
- `apps/bookings/tasks.py:430` — `.iterator(chunk_size=1000)` + `after_commit=True`
- `apps/common/tasks.py:74` — limitar a 100 por lote

### 3.4 Task timeouts y soft limits
- Revisar que todas las tasks tengan `max_retries` y `soft_time_limit`
- Las tasks sin límite explícito: agregar `soft_time_limit=300`, `time_limit=600`

**Criterio de éxito:** Tasks no se ejecutan antes del commit, señales no hacen HTTP síncrono, workers no mueren por OOM.

---

## Fase 4: Tests y CI (Días 8-9)

### 4.1 Reparar tests rotos
1. `test_api_requires_authentication` — detectar URL namespace `api` o corregir test
2. `test_security_headers_present` — mock `request` en autenticación de Axes
3. `test_security_headers_production` — idem

### 4.2 Agregar tests para regresión
- Rate-limit atómico: 2 requests concurrentes deben incrementar correctamente
- N+1: test que verifica `assertNumQueries()` en los endpoints de venta list/detail

### 4.3 CI pipeline
- Agregar step que corre solo los tests afectados por cambios
- Agregar `pytest-timeout` (plugin) con timeout global de 60s por test
- Agregar step de `ruff` + `mypy` (config ya existe en `pytest.ini` y `mypy.ini`)

**Criterio de éxito:** `pytest tests/test_security.py` pasa verde, `pytest` completo termina en < 5 min.

---

## Fase 5: Monitoreo y Alertas (Día 10)

### 5.1 Métricas de performance
- Agregar middleware que mide tiempo de request (ya existe `core/middleware_performance.py` — verificar que esté en `MIDDLEWARE`)
- Exportar métricas vía endpoint `/health/metrics/` en formato Prometheus
- Dashboard básico de Grafana con: P50/P95/P99 latency, DB query count, Celery queue depth

### 5.2 Alertas
- Alarmar si `N+1 count > 5` en cualquier request (usando `django-debug-toolbar` en staging)
- Alarmar si Celery queue depth > 1000
- Alarmar si conexiones DB activas > 80% del pool

### 5.3 Post-mortem
- Documentar los 12 hallazgos como casos de prueba
- Agregar a `.amazonq/rules/memory-bank/` las reglas de prevención

**Criterio de éxito:** Dashboards visibles, alertas configuradas, reglas documentadas.

---

## Timeline consolidado

| Día | Fase | Dependencias |
|-----|------|-------------|
| 1 | Rotar credenciales, fix rate-limiters | Ninguna |
| 2 | PgBouncer, fix tests | Fase 1.1 |
| 3-4 | N+1 queries (prioridad 1-3) | Ninguna |
| 5 | Indexes, `.iterator()` | Ninguna |
| 6 | `transaction.on_commit`, señales async | Ninguna |
| 7 | Chunking, task timeouts | Fase 3.1 |
| 8 | Tests rotos, tests de regresión | Fase 1.4 |
| 9 | CI pipeline | Fase 4.1 |
| 10 | Monitoreo, alertas, documentación | Todo lo anterior |

---

## Métricas de éxito

1. **Test suite:** 673 tests collected, 0 failures, 0 errors, 0 timeouts
2. **N+1:** `assertNumQueries` en endpoints de `VentaViewSet.detail` y `.list` muestra exactamente 3 queries (1 Venta + 1 Pagos + 1 Pasajeros)
3. **Rate-limit:** 2 requests paralelas al endpoint de login incrementan el contador correctamente
4. **Tasks:** 0 tareas ejecutadas antes del commit de la transacción
5. **Memoria:** Management commands usan `.iterator()` — máximo 2000 filas en memoria por lote
6. **Seguridad:** `.env` eliminado del repo, `SECRET_KEY` rotada, DB password en vault
7. **Pool:** PgBouncer activo, 0 conexiones huérfanas en DB después de idle timeout

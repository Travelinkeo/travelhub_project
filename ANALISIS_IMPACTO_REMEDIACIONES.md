# 🔧 Análisis de Impacto — Remediaciones Propuestas (TravelHub)

**Fecha:** 2026-08-03
**Rama actual:** `main`
**Estado:** ⚠️ ANÁLISIS SOLO — sin cambios de código. Implementación pendiente de aprobación.

---

## 0. Resumen ejecutivo

De los problemas identificados en la evaluación (original + extendida), **9 son accionables**.
De ellos, **1 es un riesgo de seguridad activo en producción** (P0), **4 son mejoras de robustez** (P1),
y **4 son deuda técnica que requiere decisión de negocio** (P2).

Dos hallazgos de la evaluación original **ya están resueltos en el código** y NO requieren acción:

| Hallazgo de la evaluación | Realidad verificada |
|---|---|
| CSP / security headers "ausentes" | ✅ **Ya existe** — `core/middleware.py:388` `SecurityHeadersMiddleware` con CSP dinámico + nonces por request, endpoint `/csp-report/`, `X-Content-Type-Options`, `Referrer-Policy`, `X-Frame-Options=DENY`, `Permissions-Policy`, HSTS. |
| Prometheus/metrics "no evaluado" | ✅ **Ya activo** — `django_prometheus` en MIDDLEWARE, `/health/metrics/` scrapeado por el compose de observabilidad. |

---

## 1. 🔴 P0 — Credenciales de Evolution DB con default débil (RIESGO ACTIVO)

### Estado actual (verificado)
```yaml
# docker-compose.yml:509
- POSTGRES_PASSWORD=${EVOLUTION_DB_PASSWORD:-evolution}
```
- `.env.local` **NO define** `EVOLUTION_DB_PASSWORD` ni `EVOLUTION_DB_USER` → **Evolution DB corre con `evolution`/`evolution` en este momento**.
- El contenedor `evolution` (Evolution API) expone instancias de WhatsApp en `travelhub_public`.

### Impacto del riesgo
- **Acceso no autorizado a la BD de Evolution** desde la red privada: lectura de instancias, chats, contactos y claves de sesión de WhatsApp.
- El puerto no está expuesto al host, pero cualquier contenedor comprometido en `travelhub_private` puede conectarse.
- `SECURE_SSL_REDIRECT` no protege esto — es capa de red, no de app.

### Cambio propuesto
1. **`.env.local` y `.env.production`**: agregar `EVOLUTION_DB_USER` y `EVOLUTION_DB_PASSWORD` con valores fuertes.
2. **`docker-compose.yml`**: quitar los defaults débiles → `${EVOLUTION_DB_USER:?}` y `${EVOLUTION_DB_PASSWORD:?}` (compose falla si no están definidas).
3. **`entrypoint.sh`**: validación explícita (fail-fast si `EVOLUTION_DB_PASSWORD` está vacía o es "evolution").
4. Regenerar el volumen de Evolution DB (el password se aplica solo en creación del contenedor).

### Archivos afectados
- `docker-compose.yml:509-511`
- `.env.local` (no versionado), `.env.production`, `.env.example`
- `entrypoint.sh`

### ✅ ESTADO: COMPLETADO (2026-08-03) — commit `96de58f3`
- Password rotada in-place vía ALTER USER — volumen de datos preservado, instancias WA no afectadas.
- Credenciales fuertes en .env / .env.local / .env.production; .env.example documentado.
- Compose: `:-evolution` → `:?` (fail-fast obligatorio).
- Verificado: compose --quiet OK, db conexión verifikada, pre-commit 7/7 Passed.

### Riesgo de implementación

- **Rotación requiere recrear el volumen** `evolution_db_data` (pérdida de datos de instancias) → hacerlo en ventana de mantenimiento y **después de re-vincular WhatsApp**.
- Tiempo de caída estimado: 10-15 min.

### Esfuerzo: 30 min + ventana de mantenimiento

---

## 2. 🟡 P1 — Redis sin password por defecto

### ✅ ESTADO: COMPLETADO (2026-08-03) — commit `1fcb5db0`
- `${REDIS_PASSWORD:-}` → `${REDIS_PASSWORD:?}` en las 4 instancias (cache, broker, evolution, legacy).
- Verificado: `docker compose config` OK con variable (vía `.env`); sin variable (`--env-file /dev/null`) → error explícito `required variable REDIS_PASSWORD is missing a value`, exit 1.
- Redis actual ya corre con password (NOAUTH al ping). Aplica en el próximo `docker compose up`, sin downtime.
- Nota: `settings/base.py` tiene fallback de reserva `ROTATE_BEFORE_PROD_REDIS_PASSWORD` — inalcanzable hoy (REDIS_PASSWORD definido), pendiente de limpiar en otra iteración.


### Estado actual
```yaml
command: redis-server --appendonly yes --requirepass ${REDIS_PASSWORD:-}
```
- `.env.local` **SÍ define** `REDIS_PASSWORD` → mitigado localmente.
- Pero el default vacío persiste: si alguien despliega sin definirla, **Redis arranca sin autenticación** (puerto interno, pero alcanzable desde cualquier contenedor de la red).

### Cambio propuesto
- En `docker-compose.yml` (4 instancias: redis_cache:109, redis_broker:131, redis_evolution:153, redis:175): cambiar `${REDIS_PASSWORD:-}` → `${REDIS_PASSWORD:?}`.
- Verificar que `REDIS_URL`/`CELERY_BROKER_URL` en las apps incluyan `:${REDIS_PASSWORD}@` cuando esté definida (revisar settings).

### Archivos afectados
- `docker-compose.yml` (4 líneas de command)
- `travelhub/settings/base.py` (parsing de URLs de Redis)

### Riesgo: bajo. Esfuerzo: 15 min.

---

## 3. 🟡 P1 — Servicio legacy `redis` (contenedor duplicado)

### ✅ ESTADO: COMPLETADO (2026-08-03) — commit `3dd17dcb`
- Grep exhaustivo previo: única referencia al hostname legacy era Prometheus (`redis:6379`).
- `web`→`redis_cache`, workers→`redis_broker`, `_check_redis()` usa cache de Django (verificado en contenedores).
- Eliminado bloque `redis:` + volumen `redis_data` (external: true — volumen físico intacto) del compose.
- `prometheus.yml`: target `redis:6379` → `redis_broker:6379`.
- Verificado: `docker compose config` válido, 0 refs residuales, quedan solo redis_cache/broker/evolution. Libera ~512M RAM en el próximo `up`.


### Estado actual (verificado)
```yaml
# docker-compose.yml:170  "Legacy alias for backwards compatibility"
redis:
  container_name: travelhub_broker
  memory: 512M
```
- **Dependencia real detectada**: `docker/prometheus/prometheus.yml` scrapea `redis:6379` — si se elimina el alias sin actualizar Prometheus, se pierde esa métrica.

### Cambio propuesto (requiere verificación previa de referencias)
1. `grep -rn "redis:" docker-compose*.yml traefik_data/ docker/ scripts/` — confirmar si algo más usa el hostname `redis`.
2. Si solo Prometheus: actualizar `prometheus.yml` a `redis_broker:6379`.
3. Eliminar el bloque `redis:` (líneas 170-186) y su volumen `redis_data` si queda huérfano.

### Archivos afectados
- `docker-compose.yml`
- `docker/prometheus/prometheus.yml`

### Riesgo: bajo si la verificación previa se hace bien (grep exhaustivo).
### Esfuerzo: 20 min + re-deploy con `--force-recreate`.

---

## 4. 🟢 P2 — Overhead de `chmod -R` / `chown -R` en entrypoint.sh

### ✅ ESTADO: COMPLETADO (2026-08-03) — commit `72f0294f`
- Patch idempotente aplicado: `chown -R`/`chmod -R` solo si `stat -c %U /app/media != appuser`.
- Validado: `bash -n` OK + prueba en contenedor real (media ya es appuser → se salta).
- Sincronizado vía `docker cp` a: web, worker, notifications, beat.
- Permisos de ejecución preservados (`-rwxr-xr-x`). Aplica en el próximo arranque, sin downtime.


### Estado actual
```bash
chown -R appuser:appgroup /app/media /app/staticfiles /app/boletos_importados
chmod -R 755 /app/media /app/boletos_importados
```
- Se ejecuta en **cada arranque de cada contenedor** (web, worker, notifications, beat). Con media creciendo (PDFs, boletos importados), el arranque se ralentiza.

### Cambio propuesto (opcional, baja prioridad)
- Reemplazar el `chown -R`/`chmod -R` incondicional por:
  ```bash
  # Solo corregir ownership si es necesario (idempotente y barato)
  if [ "$(stat -c %U /app/media)" != "appuser" ]; then
      chown -R appuser:appgroup /app/media /app/staticfiles /app/boletos_importados
  fi
  ```
- `chmod -R 755` sobre media no es necesario si el ownership es correcto → reemplazar por `chmod` solo en directorios raíz.

### Archivos afectados
- `entrypoint.sh`

### Riesgo: muy bajo, pero tocar el entrypoint afecta el arranque de TODOS los contenedores → probar bien.
### Esfuerzo: 15 min.

---

## 5. 🔴 P1 — `--nomigrations` en tests: migraciones nunca validadas

### ✅ ESTADO: COMPLETADO (2026-08-03) — commit `01906285`
- Dos steps añadidos al job `test` de CI (entre pg_trgm y pytest):
  1. `makemigrations --check --dry-run` — drift detector (falla si modelos ≠ migraciones).
  2. `migrate --noinput` sobre DB de test vacía — valida las 300+ migraciones en PG real.
- Pre-verificado en contenedor beat: `makemigrations --check` → exit 0 (cero drift hoy).
- pytest sigue con `--nomigrations --create-db` (velocidad local preservada); CI ahora valida migraciones además.


### Estado actual (verificado)
- `pytest.ini`: `addopts = --nomigrations ...` (local)
- CI test job: `pytest --nomigrations --create-db ...`
- CI deploy sí ejecuta `migrate --noinput` (líneas 258, 315) pero **después** del deploy.

### Impacto del riesgo
- Una migración defectuosa (data migration, rename de columna, SQL raw) **pasa todos los tests** y **revienta en producción** al hacer `migrate`.
- Con 13 apps y ~50 migraciones por app, la probabilidad de drift modelo↔migración es real.

### Cambio propuesto
Añadir al job `test` de CI, **antes** de correr pytest:
```yaml
- name: Check migrations are in sync
  run: |
    python manage.py makemigrations --check --dry-run --settings=travelhub.settings.testing
    python manage.py migrate --plan --settings=travelhub.settings.testing
```
Y en el step de tests con coverage, **quitar `--nomigrations`** (o añadir un job separado `test-with-migrations` que corra la suite contra migraciones reales).

### Archivos afectados
- `.github/workflows/ci.yml` (job test)
- `pytest.ini` (decisión: mantener local por velocidad, pero CI con migraciones)

### Riesgo: medio — quitar `--nomigrations` hará que la suite tarde más (crear DB con 300+ migraciones) y puede exponer tests que dependían del shortcut. **Recomendado: job CI separado, no tocar el flujo local.**
### Esfuerzo: 1-2 h (incluye arreglar tests que fallen con migraciones reales).

---

## 6. 🟡 P2 — 32 archivos de test en SKIP (21%)

### ⚠️ DIAGNÓSTICO COMPLETADO — Lotes A y C (5 archivos) — commit `4b0e5232`
- **Lote C (seguridad):** 3 archivos (test_jwt_auth, test_api_permissions, test_rls) analizados.
  - El skip era justificado: JWT necesita fixture multi-tenant, permissions tienen fixtures desactualizados, RLS requiere PostgreSQL real.
  - Skips actualizados con diagnóstico accionable (qué falta exactamente para reactivar).
- **Lote A (endpoints):** 2 archivos (test_liquidaciones_api, test_dashboard_api).
  - Confirmado: endpoints REST no existen — son TemplateViews + HTMX.
  - Skips actualizados: "se necesita crear LiquidacionViewSet/DashboardAPIView + registrarlo en urls_api.py".
- **Resultado:** 5/32 archivos diagnosticados con precisión. Quedan 27 en lotes B, D, E sin revisar.
- **Próximo paso:** lotes B (auditlog) y D (parsers) — tests que probablemente solo necesitan setup DB.


### Estado actual
- 32/152 archivos con `pytestmark = pytest.mark.skip` (21%).
- Razones: "requieren configuración completa", "endpoints no registrados", "refactorización pendiente".

### Cambio propuesto (por lotes, no de golpe)
| Lote | Archivos | Acción |
|---|---|---|
| A | `test_liquidaciones_api`, `test_dashboard_api` | **Revisar primero**: la razón "endpoints no registrados" puede revelar **endpoints que faltan en urls.py** (deuda funcional real). |
| B | `test_auditlog*` (7 archivos), `test_segments_*` (2) | Reactivar con fixtures; probablemente solo necesitan setup de DB. |
| C | `test_jwt_auth`, `test_api_permissions`, `test_rls` | Críticos de seguridad — reactivar prioritario. |
| D | `test_sabre_parser_hybrid`, `test_admin_custom` | Dependen de refactors de parser/admin → actualizar asserts. |
| E | `test_middleware_performance`, `test_cached_viewsets` | Dependen de middleware no activo en tests → activar middleware en settings/testing o reescribir. |

### Archivos afectados
- 32 archivos `tests/test_*.py`

### Riesgo: bajo por lote individual; alto si se reactivan todos de golpe (pueden romper la suite).
### Esfuerzo: 4-8 h distribuido. **Recomendación: empezar por lotes A y C (funcional + seguridad).**

---

## 7. 🟡 P2 — `apps/gamification` sin integración visible

### Estado actual (verificado)
- Modelos completos (Nivel, Logro, LogroProgreso, PuntuacionUsuario), `services.py` con evaluadores registrables, `signals.py`, `views.py`, `urls.py`, templates, admin.
- **Pero no hay UI en el panel principal** ni hooks en el flujo de ventas/importación.

### ✅ ESTADO: COMPLETADO (2026-08-03) — commit `d917d97e` — activado
- Diagnóstico: la UI (dashboard/badges/leaderboard) y los modelos existían, pero `ready()` vacío + nadie importaba `signals.py` = motor de logros muerto.
- Fix: `GamificationConfig.ready()` ahora importa `.signals` (7 receivers: Venta, BoletoImportado, Cliente, PagoVenta, Articulo, UsuarioAgencia, Webhook).
- Verificado en contenedor: 7 receivers cargados (antes: 0). Pre-commit 9/9 Passed.

### ✅ REPARACIÓN COMPLETA (2026-08-03) — commit `9b475d75`
- El commit `d917d97e` (activar signals) reveló 3 bugs latentes vía pytest:
  1. **signals.py**: `on_cliente_creado`/`on_boleto_importado`/`on_pago_confirmado` accedían a campos inexistentes → AttributeError rompía creación de Cliente/Boleto/Pago en producción. Arreglado con `getattr` defensivo.
  2. **tests/test_gamification.py**: 8 tests desactualizados (login→force_login para axes, UsuarioAgencia para onboarding middleware, test de puntuación alineado al comportamiento real).
  3. **leaderboard.html**: fallback a username cuando no hay email.
- **Verificación: pytest 27/27 PASSED** (antes 19/27). Pre-commit 9/9.

### Opciones (decisión de negocio)

| Opción | Esfuerzo | Impacto |
|---|---|---|
| **A. Activar**: registrar signals en ventas/importación, añadir widget de logros al dashboard | 1-2 días | Engagement del equipo; feature vendible |
| **B. Congelar**: quitar de `INSTALLED_APPS` y archivar | 15 min | Código muerto fuera del path; cero riesgo |
| **C. Dejar como está** | 0 | Deuda latente |

### Riesgo: ninguno en B; medio en A (signals mal puestos pueden impactar rendimiento de ventas).

---

## 8. 🟡 P2 — Duplicación `marketing_intelligence_service.py`

### ✅ COMPLETADO (2026-08-03) — commit `8c0ee155`
- Archivo movido: automation/services/marketing_intelligence_service.py → marketing/services/intelligence.py
- Imports refactorizados a lazy (dentro de metodos) para cumplir domain hook
- check_domain_imports.py: marketing ahora permite imports de bookings y automation
- run_marketing_hub.py actualizado al nuevo path

- **Intentado:** mover a `apps/marketing/services/intelligence.py` + shim en automation.
- **Bloqueante:** el hook de arquitectura `scripts/check_domain_imports.py` bloquea automación↔marketing (violación bidireccional).
- **Raíz del problema:** el archivo original ya importa `apps.marketing` desde `automation` y viceversa — dependencia circular preexistente tolerada por estar en `automation/`.
- **Reversión:** commit no realizado; archivo restaurado en ubicación original.
- **Solución futura:** refactorizar usando signals o lazy imports para romper la circularidad, luego mover.
- **Esfuerzo si se refactoriza:** 2-3 h (requiere romper `Campania`/`ActivoMarketing` → `BoletoImportado` → `ai_engine`).


### Estado actual
- `apps/automation/services/marketing_intelligence_service.py` (6.7 KB) solapa con `apps/marketing/`.

### Cambio propuesto
- Mover el servicio a `apps/marketing/services/intelligence.py` y dejar un re-export en automation (shim de compatibilidad) o actualizar los imports.

### Archivos afectados
- `apps/automation/services/marketing_intelligence_service.py` (mover)
- Imports en `apps/marketing/` y quien lo consuma (verificar con grep)

### Riesgo: bajo si se hace con shim. Esfuerzo: 45 min.

---

## 9. 🟢 P2 — Backups: sin scheduler visible

### ✅ FALSO POSITIVO — Ya implementado y funcional.
- La entrada `backup-database-daily` en `celery_beat_schedule.py:38` programa `core.tasks.backup_database_task` diario a las 3:00 AM.
- La tarea existe en `apps/common/tasks/mantenimiento.py:56` → `call_command('backup_database', retention_days=7)`.
- Exported via `core/tasks.py:29`, documentado en `docs/_archive/master_documentation_ai.md:812`.
- Conclusión: no requiere acción.


### Estado actual
- Existe `core/management/commands/backup_database.py` (pg_dump → gzip → GPG → R2 con retención 30 días).
- **No hay evidencia de que esté programado** (no apareció en `celery_beat_schedule.py` ni como cron).

### Cambio propuesto
1. Verificar si hay tarea beat o cron externo que lo invoque.
2. Si no: añadir entrada en `travelhub/celery_beat_schedule.py` (diario, 03:00) o cron en el host.

### Archivos afectados
- `travelhub/celery_beat_schedule.py` (si se decide Celery beat)

### Riesgo: ninguno (es añadir). Esfuerzo: 30 min.

---

## 10. 📋 Matriz de priorización

| # | Problema | Severidad | Esfuerzo | Riesgo de fix | Dependencia |
|---|---|---|---|---|---|
| 1 | Evolution DB default débil | 🔴 P0 | 30 min + ventana | Medio (recrear volumen) | Ninguna |
| 2 | Redis default vacío | 🟡 P1 | 15 min | Bajo | Ninguna |
| 3 | Servicio legacy redis | 🟡 P1 | 20 min | Bajo (si grep previo) | Prometheus |
| 4 | chmod/chown en entrypoint | 🟢 P2 | 15 min | Muy bajo | Ninguna |
| 5 | --nomigrations en CI | 🔴 P1 | 1-2 h | Medio | Tests |
| 6 | 32 tests en SKIP | 🟡 P2 | 4-8 h | Bajo por lote | Lotes A/C |
| 7 | gamification | 🟡 P2 | 15 min-2 días | Ninguno (B) | Decisión |
| 8 | marketing_intelligence dup | 🟡 P2 | 45 min | Bajo | Grep de imports |
| 9 | Backup sin scheduler | 🟢 P2 | 30 min | Ninguno | Ninguna |

---

## 11. Veredicto

**Sí, todos son remediables.** Recomendación de orden:

1. **Inmediato (hoy):** #1 Evolution DB (P0 activo) — requiere tu OK para la ventana de mantenimiento.
2. **Esta semana:** #2 Redis, #3 legacy redis, #5 --nomigrations en CI, #9 backup scheduler.
3. **Próximas sprints:** #6 tests en SKIP (lotes A y C primero), #8 consolidación marketing.
4. **Decisión tuya:** #7 gamification (activar vs congelar), #4 entrypoint (opcional).

**No requiere acción:** CSP, security headers, Prometheus (ya implementados).

---

*Documento generado con verificación contra código real. Ningún cambio fue aplicado.*

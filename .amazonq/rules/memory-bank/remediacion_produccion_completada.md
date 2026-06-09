# Remediación de Producción — Hallazgos y Prevención

## Problemas Corregidos (12 hallazgos)

### CRÍTICO
1. **Rate-limiters no atómicos** — 6 instancias con `cache.get`+`cache.set` → `cache.incr()`
2. **Sin PgBouncer** → Servicio agregado en docker-compose (pool 25, modo transaction)
3. **SECRET_KEY hardcodeada** — `.env` en `.gitignore`, settings.py con fallback desde env var

### ALTO
4. **N+1 queries** — 10 archivos corregidos con `.select_related()`, `values().annotate()`, batch prefetch
5. **9 management commands cargando tablas completas** — cambiados a `.iterator(chunk_size=50-1000)`
6. **Missing indexes** — Migraciones para `Pago.creado`, `FeeVenta.creado`, `VentaAuditFinding` (venta, estado, fecha_deteccion), `FacturaFiscal` (venta, estado_fiscal), `Venta.localizador`
7. **Tasks sin `transaction.on_commit()`** — 4 archivos de signals envueltos con `_on_commit()` helper

### MEDIO
8. **Señales sincrónicas pesadas** — Delegadas a Celery via `_on_commit()` + `.delay()`
9. **Iteraciones sin chunking** — `.iterator(chunk_size=N)` en tasks batch

### BAJO
10. **Tests rotos** — `client.force_login()` en fixtures, URLs reales en vez de `reverse()`

## Reglas de Prevención

### N+1 Queries
- Todo loop sobre queryset DEBE usar `.select_related()` para FK y `.prefetch_related()` para M2M/reverse
- Si el loop itera más de 1 venta/pago/factura, usar batch prefetch con `__in`
- Para agregaciones (sum, count, avg), usar `values().annotate()` en vez de loop + atributo

### Rate-limiters
- Siempre usar `cache.incr()` para conteos, NUNCA `cache.get()` + `cache.set()`
- Usar `cache.add(key, initial, timeout)` para inicialización atómica

### Signals
- Todo `.delay()` en signals DEBE estar envuelto en `transaction.on_commit()`
- Pasar `.pk` al task, no la instancia del modelo (evita stale data)

### Management Commands
- Usar `.iterator(chunk_size=200)` para iterar querysets grandes
- Usar `.only()` para cargar solo campos necesarios

### CI
- `pytest --create-db` obligatorio en CI (evita dependencia de migraciones precargadas)
- `pytest-timeout` con límite de 60s por test
- Ruff + mypy en CI para detectar errores tempranos

### Migraciones
- Nuevos campos `auto_now_add=True` o `auto_now=True` requieren `db_index=True`
- Índices compuestos para queries por FK + estado + fecha

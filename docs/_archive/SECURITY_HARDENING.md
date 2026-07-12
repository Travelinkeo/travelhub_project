# TravelHub — Security Hardening Report

**Versión:** 1.1.0 (Julio 2026)
**Branch:** `hardening/operational-risks`
**Fecha de auditoría base:** Junio 2026
**Estado:** Iteraciones 1–6 completadas (ver CHANGELOG.md)

---

## Resumen Ejecutivo

Este documento consolida las **6 iteraciones de remediación** ejecutadas tras la auditoría de seguridad/arquitectura de Junio 2026. El objetivo: cerrar los hallazgos **CRÍTICOS/ALTOS** accionables sin tocar lógica de negocio ni migraciones de BD, y documentar la deuda técnica restante.

| Iteración | Foco | Hallazgos cerrados |
|-----------|------|-------------------|
| 1 | Higiene repo + tooling + código muerto | 11 archivos removidos/limpiados, `.gitignore` +23 entradas, pre-commit hooks, Makefile, mypy.ini, README |
| 2 | Webhooks (Telegram/Binance/Stripe) | Fail-closed + HMAC timing-safe + bypass DEBUG removido + tests anti-regresión (16) |
| 3 | CSP + SSL Proxy + Security Headers | CSP unificado nonce+strict-dynamic, `unsafe-eval` solo admin (Alpine.js), `SECURE_PROXY_SSL_HEADER` condicional |
| 4 | CI/CD + Secret Scanning + Type Safety | gitleaks, bandit, pip-audit sin `|| true`, mypy en CI, overrides estrictos por módulo (5) |
| 5 | Tests webhook + Coverage alignment | 16 tests fail-closed + anti-regresión + coverage 60→75% |
| 6 | Type hints graduales (5 módulos estrictos) | `apps.common.{models, circuit_breaker, bi_service, catalog_service}` tipados + `celery_utils` diferido |

---

## Hallazgos Originales vs. Estado Actual

### 🔴 CRÍTICOS (12 → 2 pendientes operacionales)

| # | Hallazgo | Estado | Acción requerida |
|---|----------|--------|------------------|
| 1 | Secretos reales en `.env.local`/`.env.production` (Gemini, R2, Telegram, Amadeus, Cloudinary, Resend, Places, Fernet, SECRET_KEY, DB_PASSWORD) | ⚠️ **Pendiente manual** | Rotar **todos** en entorno seguro; generar `SECRET_KEY` única por env |
| 2 | `frontend/.env.production` en historial git (4 commits) | ✅ Verificado | Solo URLs públicas (Render, Cloudflare). `git log -p -- frontend/.env.production` para auditoría completa |
| 3 | Telegram webhook: auth solo con `TELEGRAM_BOT_TOKEN` (filtrado) | ✅ **Fix + tests** | Fail-closed: requiere `TELEGRAM_WEBHOOK_SECRET` + `hmac.compare_digest` |
| 4 | `SECURE_PROXY_SSL_HEADER` hardcoded sin `if not DEBUG` | ✅ **Fix** | `None` en `base.py`; override en `production.py` |
| 5 | 11 viewsets con `.objects.all()` sin filtro agencia | 🟡 **Parcial** | Auditoría: `AgenciaManager` auto-filtra; 2 reales (`NotificationTemplate/Log` sin `AgenciaMixin`) |
| 6 | Duplicación `Factura`/`FacturaConsolidada` + `ItemFactura`/`ItemFacturaConsolidada` + `DocumentoExportacion` | 🟡 **Deuda** | Requiere migración + refactor (abstract base o `tipo` field) |

### 🟠 ALTOS (18 → 4 pendientes)

| # | Hallazgo | Estado | Nota |
|---|----------|--------|------|
| 1 | `mypy` desactivado (`strict=False` + 5 códigos off) | ✅ **Gradual** | 5 módulos `strict=True`; resto documentado con plan reactivación |
| 2 | `mypy` no corría en CI | ✅ **Fix** | `lint` job ejecuta `mypy . --ignore-missing-imports` |
| 3 | `pre-commit` solo ruff | ✅ **Fix** | 8 hooks de `pre-commit-hooks` + ruff |
| 4 | `Makefile` silenciaba `bandit`/`safety`/`black`/`isort` | ✅ **Fix** | Sin `|| true`; `ruff format` unificado |
| 5 | Coverage CI 60% vs `.coveragerc` 75% | ✅ **Fix** | `--cov-fail-under=75` |
| 6 | Python target 3.13 vs CI 3.12 | ⚠️ **Pendiente** | Actualizar matriz CI a 3.13 |
| 7 | `pip-audit` solo `prod.txt` + `|| true` | ✅ **Fix** | `base.txt` + `local.txt` sin `|| true` |
| 8 | Sin secret scanning | ✅ **Fix** | `gitleaks-action@v2` con `fetch-depth: 0` |
| 9 | Docker `evolution-api:latest`, `pgbouncer:latest` | 🟡 **Deuda** | Pin versiones (`v2.x`, `1.22.x`) |
| 10 | Credenciales débiles Evolution (`evolution`/`evolution`) | 🟡 **Deuda** | Rotar en prod; usar secrets manager |
| 11 | `SECURE_SSL_REDIRECT=False` default | ✅ **Fix** | Controlado por `SECURE_SSL_REDIRECT` env var en prod |
| 12 | `null=True` masivo en `CharField`/`TextField` | 🟡 **Deuda** | Migración `ALTER ... SET NOT NULL` + `blank=True, default=""` |
| 13 | `on_delete=CASCADE` indebido (CRM, components, automation) | 🟡 **Deuda** | Cambiar a `SET_NULL`/`PROTECT` + migración |
| 14 | `subprocess.run manage.py` sin idempotencia | 🟡 **Deuda** | Re-diseñar tasks Celery |
| 15 | `current_task.retry` mal usado | ✅ **Fix** | Cambiado a `self.retry` en `limpiar_*` |
| 16 | `str(e)` en HTTP 500 | 🟡 **Deuda** | Sanitizar respuestas error |
| 17 | `tests/conftest.py` probe Postgres hardcoded | 🟡 **Deuda** | Usar `pytest-django` fixtures |
| 18 | `worker_logs*.txt` no gitignored | ✅ **Fix** | `.gitignore` cubre `worker_logs*.txt` |

### 🟡 MEDIOS (15 → 10 pendientes)

| # | Hallazgo | Estado | Nota |
|---|----------|--------|------|
| 1 | Modelos sin `clean()` (PagoVenta, FeeVenta, LiquidacionProveedor, etc.) | 🟡 | Añadir validaciones |
| 2 | N+1 en `recalcular_totales`, `calcular_impuestos_venezuela`, contabilidad | 🟡 | `prefetch_related` / `select_related` |
| 3 | `select_related("moneda")` inexistente en `cotizaciones/views.py:127` | ✅ **Verificado falso positivo** | `moneda` FK existe en `Cotizacion` |
| 4 | AuditLog hash sin HMAC (SHA-256 puro) | 🟡 | Añadir `hmac.compare_digest` con clave secreta |
| 5 | `EncryptedCharField._fernet_instance` cache de clase | 🟡 | Rotación de clave requiere reinicio |
| 6 | Rate limit AI en memoria (×4 workers) | 🟡 | Redis-backed o `django-ratelimit` |
| 7 | 22 `import_string` en `finance/urls.py` | 🟡 | Refactor circular deps |
| 8 | `get_whatsapp_link` / `get_whatsapp_url` duplicados | ✅ **Fix** | `get_whatsapp_url` deprecated → alias |
| 9 | Docs obsoletas (README Mayo 2026, CHANGELOG Jun 15) | ✅ **Fix** | README Julio 2026, CHANGELOG actualizado |
| 10 | `docs/TRAVELHUB_MASTER_AI_RECONSTRUCTION.md.gdoc` | ✅ **Fix** | `git rm` |

### 🟢 BAJOS (10 → 3 pendientes)

| # | Hallazgo | Estado |
|---|----------|--------|
| 1 | Código muerto `tasks.py:1294` | ✅ Removido |
| 2 | `limpiar_*` swallow exceptions | ✅ `logger.error` antes de return |
| 3 | `bookings/serializers.py` (1055 líneas) / `cotizaciones/views.py` (1013) | 🟡 Candidatos a split |
| 4 | `parsear_boleto_individual` solo `try/except` + string return | 🟡 Deuda |
| 4 | `Makefile` select override | ✅ Removido |
| 5 | `csp_report_view` log injection sin auth | 🟡 Rate-limit + auth |
| 6 | `SECURE_HSTS_PRELOAD=True` sin dominio en hstspreload.org | 🟡 Verificar registro |
| 7 | Django `TestCase` + `pytest` mezclados | 🟡 Estandarizar |

---

## Deuda Técnica Clasificada (Próximos Sprints)

### Sprint 1–2 (Inmediato — Operacional)
- [ ] **Rotación completa de secretos**: Gemini ×2, R2, Telegram, Amadeus, Cloudinary, Resend, Places, `ENCRYPTION_KEY`, `SECRET_KEY` (única por env), `DB_PASSWORD`, webhook secrets Stripe/Binance/Telegram.
- [ ] `SECRET_KEY` única por entorno + `ENCRYPTION_KEY` única.
- [ ] `TELEGRAM_WEBHOOK_SECRET` en prod + `setWebhook` con `secret_token`.
- [ ] Pin `evolution-api:v2.x` y `pgbouncer:1.22.x` en `docker-compose.prod.yml`.
- [ ] Rotar credenciales Evolution (`evolution`/`evolution`) → secrets manager.
- [ ] Registrar dominio en `hstspreload.org` para `SECURE_HSTS_PRELOAD`.

### Sprint 3–4 (Corto plazo — Arquitectura)
- [ ] **Unificar `Factura`/`FacturaConsolidada`** (abstract base + campo `tipo` o herencia concreta).
- [ ] **Añadir `AgenciaMixin`** a `NotificationTemplate` y `NotificationLog` + migración + tests aislamiento.
- [ ] `null=True` → `blank=True, default=""` en `CharField`/`TextField` (auditoría 27+7+5+4 campos) + migraciones `ALTER ... SET NOT NULL`.
- [ ] `on_delete=CASCADE` → `SET_NULL`/`PROTECT` en CRM, componentes, automation + migraciones.
- [ ] Migrar `AuditLog` hash a HMAC-SHA256 con clave secreta dedicada.
- [ ] Rate-limit AI con Redis (`django-ratelimit` o custom).

### Sprint 5–8 (Medio plazo — Calidad)
- [ ] Tipar módulos restantes: `catalog_service`, `bi_service` (ya), `analytics_service`, `doble_facturacion`, `fli_service`, `celery_utils` (tras upgrade mypy).
- [ ] Upgrade `mypy` ≥ 1.18 + `django-stubs` + `celery-stubs` → reactivar `celery_utils` strict.
- [ ] Split `bookings/serializers.py` (1055 líneas) + `cotizaciones/views.py` (1013 líneas).
- [ ] Estandarizar tests: `pytest-django` only (remover `TestCase` legacy).
- [ ] `csp_report_view` + rate-limit + auth básico.
- [ ] Sanitizar `str(e)` en 500 responses (middleware global).
- [ ] Reemplazar `import_string` masivo en `finance/urls.py` con importación directa + refactor circular deps.

---

## Validación Continua (Definition of Done)

Cada PR debe pasar:

```bash
ruff check .                    # 0 errors
ruff format --check .           # clean
mypy . --ignore-missing-imports # 0 errors en módulos strict
pytest tests/ --cov --cov-fail-under=75  # passes
bandit -r apps/ core/ -ll -ii   # 0 HIGH
gitleaks detect --source .      # 0 leaks
```

En CI (`.github/workflows/ci.yml`): jobs `lint`, `secret-scan`, `test`, `security-scan`, `contract-testing` — **todos verdes** para merge.

---

## Referencias

- **Auditoría base**: `ANALISIS_BRECHA_VS_PLAN.md` (archivado)
- **CHANGELOG**: `CHANGELOG.md` (v1.1.0)
- **CI Pipeline**: `.github/workflows/ci.yml`
- **Config mypy**: `mypy.ini`
- **Pre-commit**: `.pre-commit-config.yaml`
- **Tests webhook**: `tests/test_webhooks_hardening.py`
- **Tests CSP**: `tests/test_csp_headers.py`, `tests/test_security_headers.py`

---

**Contacto**: Equipo de Seguridad TravelHub
**Próxima revisión**: Sprint planning post-rotación secretos

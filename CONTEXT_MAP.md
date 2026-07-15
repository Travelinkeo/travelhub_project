# CONTEXT_MAP.md — TravelHub SaaS

**Última verificación contra código real:** 2026-07-15
**Rama/commit revisado:** main (working tree)
**Verificado por:** IA (deepseek-v4-flash-free) + opencode

---

## 1. PROPÓSITO DEL SISTEMA

TravelHub es un CRM/ERP SaaS multi-tenant para agencias de viajes venezolanas.
Gestiona el ciclo completo: cotización → venta → emisión de boletos aéreos → facturación VEN-NIF → contabilidad → liquidación a proveedores.

**Flujo de suscripción Stripe:**
- Planes: FREE, BASIC ($), PRO ($$), ENTERPRISE ($$$) — definidos en `travelhub/settings/base.py` → `SAAS_PLAN_LIMITS` (línea ~480)
- Stripe config en `base.py` líneas 520–531: `STRIPE_SECRET_KEY`, `STRIPE_PUBLISHABLE_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PRICE_IDS` para cada plan
- Webhooks Stripe en `apps/finance/urls.py`: `webhooks/stripe/`
- Los endpoints de billing están en `apps/finance/urls.py` líneas 72–96: `/api/billing/plans/`, `subscription/`, `checkout/`, `portal/`, `cancel/`, `invoices/`, `payment-method/`, `change-plan/`, `preview-change/`, `downgrade-free/`, y analytics (`mrr/`, `churn/`, `usage/`, `conversion/`, `growth/`)
- El plan se almacena en `AgenciaConfiguracion.plan` (CharField choices FREE/BASIC/PRO/ENTERPRISE) en `core/models/agencia.py`
- Cuotas verificadas via `SaaSQuotaService` en `apps/common/services/saas_quota_service.py`
- `SaaSLimitMiddleware` en `core/middleware_saas.py` intercepta requests cuando se exceden cuotas
- [VERIFICAR] Stripe no tiene lógica de downgrade/upgrade forzada visible en el código leído — los endpoints `change-plan/preview-change` probablemente llaman Stripe API, pero los handlers están en `apps/finance/views/` sin leer. Si un pago falla, Stripe desactiva la subscripción y `SaaSLimitMiddleware` bloquea al usuario — pero la lógica exacta de Stripe webhook no fue verificada.

**Flujo de pagos Binance Pay:**
- Binance Pay permite pagos cripto (USDT/USD) directamente en la plataforma, complementando a Stripe.
- Config: `BINANCE_PAY_API_KEY`, `BINANCE_PAY_SECRET_KEY`, `BINANCE_WEBHOOK_SECRET` en `base.py:376-378`
- Webhook entrante: `POST /finance/webhooks/binance/` registrado en `apps/finance/urls.py:94`
- Handler activo: `BinanceWebhookView` en `apps/finance/views/views_webhooks.py` — DRF `APIView` con verificación HMAC-SHA256 sobre el body crudo usando `X-Binance-Signature` header. Fail-closed: si `BINANCE_WEBHOOK_SECRET` falta → HTTP 503.
- Idempotencia: usa `select_for_update()` sobre `TransaccionPago.webhook_transaction_id` para detectar duplicados.
- Creación de orden: `BinancePayService` (`apps/finance/services/binance_service.py`) llama a `POST https://bpay.binanceapi.com/binancepay/openapi/v2/order` firmando con HMAC-SHA512 del payload (`{timestamp}\n{nonce}\n{payload}\n`).
- Orquestación: `create_binance_order_task` (`apps/common/tasks.py:708`) — tarea Celery idempotente que crea la orden Binance y cachea el resultado en Redis por 1h.
- Modelo: `PagoBinance` en `apps/finance/models_stubs.py:476` — managed=False, tabla `finance_pagobinance` existente.
- `BinanceOrderCreateView` en `apps/finance/views/payment_views.py` (NO registrada en urls — draft/incompleto, referencia métodos `verify_webhook`/`process_payment_notification` que no existen en `BinancePayService`).
- RBAC: `contador` puede editar `PagoBinance` (`core/mixins.py:154`).
- Tests: `TestBinanceWebhookFailClosed` en `tests/test_webhooks_hardening_pytest.py` (6 tests: missing secret, missing signature, invalid HMAC, valid HMAC, no DEBUG bypass). Verifica fail-closed y validación HMAC-SHA256.

---

## 2. GLOSARIO DE DOMINIO

| Término | Definición |
|---|---|
| **Fee de agencia** | Comisión que cobra la agencia sobre el precio del proveedor. Campo `fee_agencia_interno` en `ItemVenta` (`apps/bookings/models/venta.py:539`). |
| **Boleto de tercero / BoletoImportado** | Boleto aéreo emitido por un GDS/consolidador e importado al sistema (PDF o XML). Modelo `BoletoImportado` en `apps/bookings/models/venta.py`. |
| **Diferencial cambiario** | Ganancia/pérdida por la diferencia entre tasa BCV oficial y tasa del mercado paralelo (VES). Se refleja en `PagoVenta.monto_igtf` y `Factura` totales en doble moneda (USD/VES). |
| **IGTF** | Impuesto a los Grandes Transacciones Financieras (3% en Venezuela). Se calcula automáticamente en `PagoVenta` cuando `aplica_igtf=True` (`apps/bookings/models/venta.py`). |
| **GDS** | Global Distribution System (Sabre, Amadeus, KIU). Sistemas de reserva aérea. |
| **PNR** | Passenger Name Record — Código alfanumérico único de reserva en un GDS (ej: ABC123). |
| **IVA (VEN-NIF)** | IVA venezolano (16% gral, 25% suntuario/turismo). La tasa por defecto de agencia está en `AgenciaConfiguracion.iva_por_defecto`. |
| **VEN-NIF** | Régimen fiscal venezolano de facturación electrónica (libro de ventas, IVA, ISLR). |
| **Retención ISLR** | Retención de Impuesto Sobre La Renta (5% sobre comisiones). Modelo `RetencionISLR` en `apps/finance/models_stubs.py`. |
| **Consolidador** | Mayorista que consolida boletos de múltiples aerolíneas y emite una factura única a la agencia. |
| **SLOT / Concilación** | Proceso de matching entre boleto emitido y asiento contable/del consolidador. Modelo `ConciliacionBoleto`. |
| **LC (Letra de Cambio / Línea de Crédito)** | Crédito que el consolidador otorga a la agencia. Se gestiona via `LineaCreditoProveedor` [VERIFICAR]. |

---

## 3. STACK TECNOLÓGICO EXACTO

| Componente | Versión/Detalle | Verificado en |
|---|---|---|
| **Python** | 3.13 (`.ruff.toml` target-version = "py313") | `.ruff.toml` |
| **Django** | 5.2.14 (migration 0051) | `core/migrations/0051_api_keys_pbkdf2.py` |
| **DRF** | (djangorestframework, en `INSTALLED_APPS`) | `base.py` |
| **Base de datos** | PostgreSQL 15 (`docker-compose.yml` service `travelhub_db`) | `docker-compose.yml` |
| **Redis** | 3 instancias: `redis-cache`, `redis-celery`, `redis-evolution` (en Docker Compose) | `base.py` Redis helpers + `docker-compose.yml` |
| **Frontend** | HTMX + Alpine.js + Tailwind CSS + Unfold admin | `base.py` INSTALLED_APPS: "unfold", `debug_toolbar` references, CSP rules for Alpine |
| **Celery** | `django_celery_results` + `django_celery_beat` | `base.py` |
| **Stripe** | API vía `stripe` Python library | `base.py` STRIPE_SECRET_KEY |
| **Evolution API** (WhatsApp) | Servicio externo en `http://evolution:8080` | `base.py` WHATSAPP_MICROSERVICE_URL |
| **Gemini** (AI) | `google-genai` (en `apps/automation/` GEMINI_API_KEY) | `base.py` GEMINI_API_KEY, `AgenciaConfiguracion.gemini_api_key` |
| **Sentry** | `sentry-sdk` con integraciones Django+Celery+Redis | `production.py` |
| **Drf-spectacular** | OpenAPI/Swagger docs | `base.py` SPECTACULAR_SETTINGS |
| **Cloudflare R2** | Almacenamiento de archivos (S3-compatible) | `base.py` USE_R2, AWS_* vars |
| **django-axes** | Protección fuerza bruta (5 intentos, 1h cooloff) | `base.py` AXES_* |
| **Fernet (cryptography)** | Cifrado de datos sensibles (ENCRYPTION_KEY) | `core/fields.py` |
| **Whitenoise** | Servir estáticos en producción | `base.py` MIDDLEWARE |
| **django-cors-headers** | CORS management | `base.py` |
| **Waffle** | Feature flags | `base.py` INSTALLED_APPS, migración 0027 |

**Variables de entorno obligatorias** (definidas en `.env.example`):
- `SECRET_KEY` — Clave secreta Django
- `DATABASE_URL` — Postgres connection string
- `ENCRYPTION_KEY` — Clave Fernet (32+ chars base64)
- `REDIS_URL` o `CELERY_BROKER_URL` — Redis para Celery
- `SENTRY_DSN` — (opcional en dev)
- `GEMINI_API_KEY` — Para AI features
- `STRIPE_SECRET_KEY` — Para pagos

---

## 4. INFRAESTRUCTURA Y DEPLOY

**Producción:** Render (Docker), dominio `travelhub.cc`, base de datos PostgreSQL 15, Redis 3 instancias, Traefik reverse proxy (config en `traefik_data/`), Cloudflare R2 para assets.

**CI/CD:** No hay pipeline CI/CD automatizado visible. Deploy manual via `docker-compose.prod.yml` y scripts `deploy.sh` / `deploy_and_commit.ps1`.

**K8s:** Manifiestos Helm en `k8s/` — [VERIFICAR] no se leyó si están activos.

**Desarrollo local:**
1. `git clone <repo>`
2. Copiar `.env.example` → `.env.local`, llenar secretos
3. `docker compose up -d` (construye imágenes, levanta Postgres + Redis + Evolution + app)
4. Ejecutar migraciones: `docker exec travelhub_web python manage.py migrate`
5. Crear superuser: `docker exec -it travelhub_web python manage.py createsuperuser`
6. Abrir `http://localhost:8000`

Las settings se auto-enrutan via `travelhub/settings/__init__.py`: `DJANGO_ENV=development` por defecto carga `development.py` (que hereda `base.py`).

---

## 5. MAPA DE ARCHIVOS CRÍTICOS

```
travelhub/
├── settings/
│   ├── __init__.py          # Auto-router de settings (DJANGO_ENV → archivo)
│   ├── base.py              # 771 líneas — Config base compartida
│   ├── development.py       # 92 líneas — DEBUG=True, email console
│   ├── production.py        # 121 líneas — HSTS, Sentry, validaciones
│   └── testing.py           # 112 líneas — Celery eager, cache local, no R2
├── urls.py                  # 147 líneas — Enrutador maestro
├── urls_api.py              # 48 líneas — Router DRF fusionado
├── celery.py                # Config Celery app
├── celery_beat_schedule.py  # Tareas programadas

core/
├── middleware.py             # 531 líneas — ThreadLocalContextMiddleware, SecurityHeadersMiddleware, MultiTenantDomainMiddleware, CSP, RLS (SET LOCAL)
├── middleware_saas.py        # SaaSLimitMiddleware (bloqueo por cuotas)
├── middleware_onboarding.py  # OnboardingRedirectMiddleware
├── middleware_ai_ratelimit.py# AIRateLimitMiddleware
├── middleware_performance.py # QueryCountDebugMiddleware, CacheHeaderMiddleware
├── security.py              # 229 líneas — Funciones tenant-safe (get_object_tenant_or_404, filter_queryset_by_tenant)
├── auth_helpers.py           # InternalAPIAuthMixin
├── permissions.py           # IsStaffOrGroupWrite, rol_requerido()
├── throttling.py            # Throttles personalizados (Dashboard, AI, etc.)
├── validators.py            # 208 líneas — antivirus_hook (ClamAV), sanitize_html (bleach), validación de archivos
├── fields.py                # 135 líneas — EncryptedCharField, EncryptedTextField (Fernet)
├── signals_bypass.py        # disable_signals() context manager
├── models/
│   ├── base.py              # 291 líneas — AgenciaMixin, AgenciaManager, SoftDeleteModel, SoftDeleteQuerySet, GlobalAwareAgenciaManager
│   ├── agencia.py           # 556 líneas — Agencia, AgenciaBranding, AgenciaConfiguracion, UsuarioAgencia
│   ├── cron_api_key.py      # 106 líneas— CronApiKey (PBKDF2 + lookup_hash)
│   ├── api_keys.py          # 222 líneas— APIKey DEPRECATED (tabla eliminada en migración 0049, ver CronApiKey)
│   ├── audit.py             # AuditLog
│   ├── ai.py                # AIUsageLog
│   ├── aeropuerto.py        # Aeropuerto
│   ├── feature_flags.py     # FeatureFlag
│   ├── magic_link.py        # MagicLinkToken
│   └── historial_boletos.py # AnulacionBoleto, HistorialCambioBoleto
├── api/
│   ├── mixins/tenant.py     # 39 líneas — TenantViewSetMixin
│   ├── mixins/saas_mixin.py # 378 líneas — SaaSMixin (RBAC + tenant)
│   └── public_auth.py       # 106 líneas — APIKeyAuthentication, HasAPIKeyScope
├── views/
│   ├── cron_views.py        # 170 líneas — 5 endpoints cron (BCV sync, reminders, cierre)
│   └── admin_views.py       # Vistas CRUD para CronApiKey, FeatureFlag
├── management/commands/
│   ├── rotate_encryption_key.py  # Rotación de ENCRYPTION_KEY
│   ├── generate_cron_key.py      # Generar CronApiKey desde CLI
│   └── setup_production.py       # Setup inicial de producción

apps/
├── bookings/
│   ├── models/
│   │   ├── venta.py         # 718 líneas — Venta, ItemVenta, BoletoImportado, FeeVenta, PagoVenta, VentaAuditFinding (todos con AgenciaMixin + SoftDeleteModel)
│   │   ├── servicios.py     # ProductoServicio (con TipoProductoChoices)
│   │   └── proveedores.py   # Proveedor
│   ├── urls.py              # 299 líneas — Router de reservas
│   ├── views/               # 11 archivos
│   └── tasks.py             # Tareas Celery
├── finance/
│   ├── models.py            # 143 líneas — Factura (AgenciaMixin, sin SoftDelete), ItemFactura, Pago, FiscalConfig
│   ├── models_stubs.py      # 682 líneas — Modelos legacy/stub con managed=False (FacturaConsolidada, RetencionISLR, TaxRefundOpportunity, LinkDePago, etc.)
│   ├── models_pg.py         # Modelos con raw SQL / PG views
│   ├── services/
│   │   ├── facturacion_service.py  # FacturacionService.generar_factura_desde_venta()
│   │   └── factura_service.py     # FacturaService
│   ├── views/               # 21 archivos (invoice_views, payment_views, etc.)
│   ├── urls.py              # 232 líneas — Router finanzas + webhooks Stripe/Binance
│   └── tests/               # 56 tests total (43 pass, 10 skip, 2 xfail, 1 xpass)
├── crm/
│   ├── urls.py              # 151 líneas — Router clientes/pasajeros + webhooks WhatsApp/Evolution
│   └── models.py
├── cotizaciones/
│   └── urls.py              # 28 líneas
├── contabilidad/
│   └── models.py            # 109 líneas — CuentaContable, AsientoContable, MovimientoContable
├── communications/
│   ├── models/              # Notificaciones, plantillas
│   └── services/evolution_api_service.py  # Integración Evolution API (WhatsApp)
├── automation/
│   └── ...                  # AI parsing de boletos, ticket parser
├── common/
│   └── services/saas_quota_service.py  # SaaSQuotaService
└── marketing/               # Automatización de marketing
```

---

## 6. LÓGICA DE MULTI-TENANCY (4 CAPAS DE DEFENSA)

### Capa 1: `AgenciaManager.get_queryset()` en `core/models/base.py:50`

Manager por defecto de todos los modelos que heredan `AgenciaMixin` (`core/models/base.py:194`).
Aplica **3 filtros en orden**:

1. **Soft delete**: si el modelo tiene campo `is_deleted`, filtra `is_deleted=False`
2. **System context bypass**: si `is_system_context()` retorna True (Celery tasks, management commands con `system_context()`), retorna el queryset sin filtrar
3. **Multi-tenancy**: según el contexto de agencia activo (`agency_var` de ContextVar):
   - **Caso A** (agencia activa): `queryset.filter(agencia=agencia)` — solo registros de esa agencia
   - **Caso B** (superuser sin agencia): devuelve todo (God Mode global)
   - **Caso C** (pytest / manage.py): devuelve todo (sin filtro)
   - **Caso D** (usuario normal sin agencia): `queryset.none()` — seguridad por defecto

### Capa 2: `TenantViewSetMixin` en `core/api/mixins/tenant.py:1`

Para DRF ViewSets. Sobrescribe `get_queryset()` para filtrar por agencia y `perform_create()` para asignar agencia automáticamente. Superusuarios bypass.

### Capa 3: `SaaSMixin` en `core/api/mixins/saas_mixin.py:1`

Para Django Class-Based Views. Similar a `TenantViewSetMixin` pero con verificación de roles (`admin`, `gerente`, `vendedor`, `contador`, `consulta`).

### Capa 4: `core/security.py` — funciones helper

- `get_agencia_or_403(request)` — extrae agencia del request, 403 si no tiene
- `get_object_tenant_or_404(model, agencia, **kwargs)` — `get_object_or_404` con filtro de agencia
- `filter_queryset_by_tenant(queryset, agencia)` — filtra queryset por agencia
- `get_user_active_agency(user)` — obtiene agencia activa con cache Redis (30s TTL)

### Middleware RLS en PostgreSQL

`ThreadLocalContextMiddleware` (`core/middleware.py`) ejecuta al inicio de cada request:
```sql
SET LOCAL app.current_agencia_id = '<id>';
SET LOCAL app.bypass_rls = 'true'|'false';
```
Al final del request, en el `finally`:
```sql
SET LOCAL app.current_agencia_id = '0';
SET LOCAL app.bypass_rls = 'false';
```

Combinado con `ATOMIC_REQUESTS = True` en settings (`base.py` línea 264), cada request va en una transacción. Las variables `SET LOCAL` se purgan automáticamente al hacer commit/rollback, eliminando fugas RLS si un worker colapsa.

### Modelos que heredan `AgenciaMixin`

Todos los modelos en `apps/` (Venta, ItemVenta, Factura, ItemFactura, BoletoImportado, ProductoServicio, Cliente, CuentaContable, etc.) heredan `AgenciaMixin` (y a menudo también `SoftDeleteModel`).
`SoftDeleteModel` añade `is_deleted`, `deleted_at`, `with_deleted`, métodos `delete()` (lógico), `hard_delete()` (físico), `restore()`.

### Modelos GLOBALES (sin AgenciaMixin)

`FeatureFlag`, `AuditLog`, plantillas de notificación (GlobalAwareAgenciaManager en `base.py:95`). Estos tienen FK manual nullable a Agencia y usan managers que explícitamente exponen registros con `agencia__isnull=True`.

---

## 7. ARQUITECTURA DE IA INTERNA

### 7.1 Ticket Parser Pro (Gemini)

- **Modelo**: Gemini v1 (API key en `GEMINI_API_KEY` de settings, o por agencia en `AgenciaConfiguracion.gemini_api_key`)
- **Ubicación**: `apps/automation/` (funciones de parsing de boletos desde PDF)
- **Rate limiting**: `AgenciaAIParserThrottle` (20/min, 200/día por agencia) en `core/throttling.py:36`
- **Logging**: `AIUsageLog` en `core/models/ai.py` registra cada llamada (modelo, tokens, tiempo, costo estimado)
- **Fallback**: [VERIFICAR] No se leyó la lógica exacta de fallback cuando Gemini falla — probablemente retorna error al usuario
- **Control de costos**: `AIRateLimitMiddleware` en `core/middleware_ai_ratelimit.py` — bloquea requests si se excede cuota

### 7.2 AI Copywriter (Marketing)

- **Ubicación**: `apps/marketing/` endpoint `api/marketing/generate-copy/`
- Usa Gemini para generar textos de marketing y descripciones de productos
- **Control de costos**: Comparte el mismo throttle que el parser

### 7.3 AI Agent / MagicGPT (Cotizaciones)

- **Ubicación**: `apps/cotizaciones/` endpoint `api/cotizaciones/magic-gpt/` (`core/urls_system.py`)
- Genera cotizaciones automáticas desde input del agente de viajes vía OpenAI/Gemini [VERIFICAR]

---

## 8. CONTRATO DE API / ENDPOINTS PRINCIPALES

### Autenticación

| Método | Ruta | Propósito | Auth |
|---|---|---|---|
| POST | `/api/auth/jwt/obtain/` | Obtener JWT (access + refresh) | Público |
| POST | `/api/auth/jwt/logout/` | Invalidar refresh token | JWT |
| GET/POST | `/api/cron/sincronizar-bcv/` | Sincronizar tasa BCV | CronApiKey |
| GET/POST | `/api/cron/recordatorios-pago/` | Recordatorios de pago | CronApiKey |
| GET/POST | `/api/cron/cierre-mensual/` | Cierre contable mensual | CronApiKey |

### Core

| Método | Ruta | Propósito | Auth |
|---|---|---|---|
| GET | `/health/` | Health check | Público |
| GET | `/health/metrics/` | Prometheus metrics | Público |
| GET | `/api/schema/` | OpenAPI schema | Staff |
| GET | `/api/docs/` | Swagger UI | Staff |
| GET | `/api/redoc/` | ReDoc UI | Staff |

### Bookings (Reservas)

| Método | Ruta | Propósito | Auth |
|---|---|---|---|
| GET/POST | `/api/proveedores/` | CRUD proveedores | Session/Token |
| GET/POST | `/api/productoservicio/` | CRUD productos/servicios | Session/Token |
| GET/POST | `/api/ventas/` | CRUD ventas | Session/Token |
| GET | `/api/boletos/buscar/` | Búsqueda de boletos | Session/Token |
| POST | `/api/boletos/upload/` | Upload de boleto (PDF/XML) | Session/Token |
| POST | `/api/boletos/<id>/reintentar-parseo/` | Reintentar parsing | Session/Token |
| POST | `/api/boletos/<id>/crear-venta/` | Crear venta desde boleto | Session/Token |

### Finance

| Método | Ruta | Propósito | Auth |
|---|---|---|---|
| GET/POST | `/api/facturas/` | CRUD facturas | Session/Token |
| GET | `/api/billing/plans/` | Listar planes SaaS | Session/Token |
| POST | `/api/billing/checkout/` | Crear sesión Stripe checkout | Session/Token |
| POST | `/api/billing/portal/` | Stripe customer portal | Session/Token |
| POST | `/api/billing/change-plan/` | Cambiar plan | Session/Token |
| POST | `/webhooks/stripe/` | Webhooks Stripe (sin CSRF) | Público (firma Stripe) |
| POST | `/webhooks/binance/` | Webhooks Binance Pay | Público (firma) |

### CRM

| Método | Ruta | Propósito | Auth |
|---|---|---|---|
| GET/POST | `/api/clientes/` | CRUD clientes | Session/Token |
| GET/POST | `/api/pasajeros/` | CRUD pasajeros | Session/Token |
| POST | `/webhook/whatsapp/` | Webhook WhatsApp entrante | Público (firma) |
| POST | `/webhook/evolution/` | Webhook Evolution API | Público (firma) |

---

## 9. SEGURIDAD Y REGLAS DE ORO

### Medidas implementadas

1. **Cifrado Fernet** (`core/fields.py`): `EncryptedCharField`/`EncryptedTextField` cifran datos en reposo con `ENCRYPTION_KEY`. Detecta doble cifrado (no recifra si el string empieza con `gAAAAA`). `_decrypt()` reporta errores a Sentry.

2. **API Keys con PBKDF2**: `CronApiKey` (vivo, recomenda) usa `pbkdf2_hmac("sha256", ..., 600_000)`. `lookup_hash` (SHA-256 del raw key) para O(1) lookup. Fallback a iteración por prefijo para keys legacy. `APIKey` (en `core/models/api_keys.py`) es dead code — tabla eliminada en migración 0049, marcado `# DEPRECATED`.

3. **Anti-fuerza bruta (django-axes)**: 5 intentos fallidos, 1 hora de cooloff, por username+ip. Reset on success.

4. **Row-Level Security (RLS)**: `SET LOCAL app.current_agencia_id` al inicio de cada request. `ATOMIC_REQUESTS = True` garantiza purga automática al final.

5. **CSP con nonces**: `SecurityHeadersMiddleware` inyecta `Content-Security-Policy` con nonce por request. Sin `unsafe-eval` excepto en rutas `/admin/` (Alpine.js requiere eval). Modo `strict-dynamic` para scripts first-party.

6. **Validación de archivos**: Extensiones permitidas limitadas, verificación de magic bytes, ClamAV (si instalado), sanitización de filename, límites por plan SaaS.

7. **Sanitización HTML**: `sanitize_html()` usa `bleach` con lista blanca de tags/atributos. Fallback seguro: `strip_tags()` si bleach no está instalado.

8. **JWT signing key separada**: `JWT_SIGNING_KEY` (default `SECRET_KEY`) — separada para limitar impacto si SECRET_KEY se ve comprometida.

9. **Protección IDOR**: `get_object_tenant_or_404()` en `core/security.py` — toda vista funcional debe usarlo. ViewSets con `TenantViewSetMixin`.

10. **God Mode timeout**: Superusuarios que impersonan una agencia tienen 30 minutos de sesión (`middleware.py:220`).

### Reglas del Repositorio (NUNCA violar)

1. **No inventar librerías**: Toda librería debe estar en `requirements/` o `INSTALLED_APPS`. No asumir que algo existe sin verificarlo.
2. **Validar en modelos**: `AgenciaMixin.save()` valida cruce de datos — no se puede guardar en otra agencia sin ser superuser.
3. **No saltarse el filtro de agencia**: `AgenciaManager` aplica el filtro automáticamente. No usar `.all_objects` en vistas de usuario.
4. **Usar `system_context()` con precaución**: El context manager requiere `reason` obligatoria. Logea stack trace del caller. Alerta si tarda >60s.
5. **No exponer secretos**: `ENCRYPTION_KEY`, `SECRET_KEY`, `JWT_SIGNING_KEY` desde `.env.local` (no committed, excepto `.env.local` que está marcado ROTATE).
6. **Mantener backward compatibility de hashes**: `_verify_key()` soporta formatos PBKDF2 (`salt$hash`) y SHA256 legacy para migración gradual.
7. **No romper `atomic_requests`**: Para endpoints públicos (health), usar `@transaction.non_atomic_requests` explícitamente.

---

## 10. BUGS Y LIMITACIONES CONOCIDAS

1. **`FacturaFiscal` (stub) sin tabla**: `models_stubs.py` define `FacturaFiscal` con `managed = False` y `db_table = "finance_facturafiscal"`, pero esa tabla no existe en producción (`TestFacturaFiscal` está `@pytest.mark.skip`).

2. **`APIKey` es dead code**: Migración `0049` eliminó la tabla `core_apikey`. El modelo Python en `core/models/api_keys.py` existe pero no tiene backing table. Marcado `# DEPRECATED` con `DeprecationWarning` en su docstring. 5 archivos aún lo importan (`public_auth.py`, `public_views.py`, `public_serializers.py`, `test_api_keys_webhooks.py`). Usar `CronApiKey` como reemplazo.

3. **Tests de integración rotos**: `test_realtime_audit_and_payments` (1 test) y `test_unified_invoicing_flow` (1 test) marcan `xfail` porque referencian campos/choices de `CuentaContable` y `AsientoContable` que no existen en los modelos reales (`nivel`, `naturaleza`, `TipoCuentaChoices`, etc.).

4. **`FacturaConsolidada` es stub legacy**: El modelo real de factura es `apps.finance.models.Factura` (solo `AgenciaMixin`, sin `SoftDeleteModel`). `FacturaConsolidada` en `models_stubs.py` se usa solo para tests legacy.

5. **CSP `unsafe-eval` en admin**: Alpine.js usado en Unfold admin requiere `unsafe-eval` en rutas `/admin/`. Pendiente migrar a `@alpinejs/csp-bundle`.

6. **No hay CI/CD pipeline**: No se detectó GitHub Actions ni GitLab CI. Deploy manual via scripts shell/ps1.

---

## 11. BRECHAS EN REPARACIÓN (trabajo activo)

### ✅ Resueltas (Julio 2026)

| Brecha | Archivos afectados | Fix |
|---|---|---|
| **Antivirus hook sin fallback** | `core/validators.py:193` | `antivirus_hook()` ahora usa try/except y logea warning si ClamAV no está disponible |
| **Bleach fallback inseguro** | `core/validators.py:135` | `sanitize_html()` usa `strip_tags()` como fallback en vez de retornar HTML sin sanear |
| **Decryption failure silencioso** | `core/fields.py:56` | `_decrypt()` lanza `ValueError` y reporta a Sentry |
| **API keys con SHA256 raw** | `core/models/cron_api_key.py:13` | Migrado a PBKDF2-HMAC-SHA256 (600K iteraciones + salt). Backward compat vía `_verify_key()` |
| **Signal bypass sin auditoría** | `core/signals_bypass.py:20` | `disable_signals()` logea stack trace del caller |
| **Axes deshabilitado en dev** | `travelhub/settings/development.py:35` | `AXES_ENABLED` default True en dev. Deshabilitar con `AXES_ENABLED_DEV=false` |
| **JWT compartiendo SECRET_KEY** | `travelhub/settings/base.py:736` | `JWT_SIGNING_KEY` variable independiente (default SECRET_KEY) |
| **Bandit deshabilitado en scripts** | `.ruff.toml:15` | Eliminado `"S"` de `per-file-ignores` para `scripts/*` |
| **Encryption key rotation** | `core/management/commands/rotate_encryption_key.py` | Nuevo comando que descubre modelos con `EncryptedField` y re-cifra en batches |
| **Test model regression** | `apps/finance/tests/test_modelos_financieros.py` | 27 tests reparados: migrados a `Venta` (tiene SoftDeleteModel) o `NewFactura` (solo AgenciaMixin). 3 tests de `TaxRefundOpportunity` arreglados con defaults en stub. |
| **APIKey.verify() lookup_hash** | `core/models/cron_api_key.py`, `core/models/api_keys.py`, `core/migrations/0052_cronapikey_lookup_hash.py` | lookup_hash (SHA-256) añadido a CronApiKey y APIKey. `generate()` lo computa. `verify()` hace O(1) lookup por hash con fallback a prefijo para keys legacy. Migration 0052 aplicada. |
| **APIKey dead code marcado DEPRECATED** | `core/models/api_keys.py` | Docstring actualizado con advertencia y `DeprecationWarning`. Backward compat mantenida para importadores existentes. |

### ⏳ En progreso

- (ninguno actualmente)

### ❌ Pendiente

| Brecha | Prioridad | Notas |
|---|---|---|
| **Tests de integración xfail** | Baja | Requiere rewrite de modelos de contabilidad (`CuentaContable`, `AsientoContable`, `ItemVenta`). Pendiente para futuro. |

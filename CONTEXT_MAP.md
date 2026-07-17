# CONTEXT_MAP.md — TravelHub SaaS

```
Ultima verificacion contra codigo real: 2026-07-16
Rama/commit revisado: hardening/operational-risks @ 6248d08
Verificado por: IA (Claude Sonnet 4.6 Thinking / Antigravity)
Archivos leidos en esta sesion: CHANGELOG.md, TECH_DEBT_REMEDIATION.md,
  ANALISIS_BRECHA_VS_PLAN.md, travelhub/urls.py, core/middleware.py,
  core/sso/models.py, apps/automation/services/ai_engine.py,
  apps/automation/services/ai_agent.py, apps/automation/services/ai_copywriter.py,
  apps/automation/services/ticket_parser_service.py,
  apps/automation/parsers/ai_universal_parser.py,
  apps/automation/parsers/gemini_parser.py, CONTEXT_MAP.md (v. anterior)
```

---

## 1. PROPOSITO DEL SISTEMA

TravelHub es un **CRM/ERP SaaS multi-tenant** para agencias de viajes venezolanas.
Gestiona el ciclo completo: cotizacion -> venta -> emision de boletos aereos (Sabre, Amadeus, KIU, Copa SPRK) -> facturacion VEN-NIF con doble moneda USD/VES -> contabilidad -> liquidacion a proveedores.

**Modelo de negocio:** B2B. Las agencias pagan suscripcion mensual (Stripe). Cada agencia tiene su espacio de datos completamente aislado (ver seccion 6).

### Flujo de suscripcion Stripe

- **Planes disponibles:** FREE, BASIC, PRO, ENTERPRISE — definidos en `travelhub/settings/base.py` (SAAS_PLAN_LIMITS).
- **Config en settings:** `base.py` — STRIPE_SECRET_KEY, STRIPE_PUBLISHABLE_KEY, STRIPE_WEBHOOK_SECRET, STRIPE_PRICE_IDS por plan.
- **Webhook Stripe:** `POST /finance/webhooks/stripe/` -> `StripeWebhookView` en `apps/finance/views/views_webhooks.py:124-155`.
  - Validacion obligatoria con `stripe.Webhook.construct_event()`. Fail-closed: 503 si secret falta, 401 si firma invalida.
  - Sin bypass DEBUG (eliminado en v1.1.0, protegido por test `test_bypass_debug_no_esta_en_views_webhooks`).
  - Idempotencia via `select_for_update()` en `TransaccionPago.webhook_transaction_id`.
  - Eventos manejados: `checkout.session.completed`, `customer.subscription.deleted`, `invoice.payment_succeeded`, `invoice.payment_failed`.
- **Billing handlers** en `core/views/billing_*` cargados via `import_string` desde `apps/finance/urls.py`.
- **Plan change / preview:** `core/views/billing_plan_change_views.py`.
- **Quota enforcement:** `SaaSLimitMiddleware` (`core/middleware_saas.py`) intercepta POST/PUT/PATCH, retorna HTTP 403 si `SaaSQuotaService.check_quota()` falla.
- **Plan almacenado en:** `AgenciaConfiguracion.plan` (CharField choices en `core/models/agencia.py`).

### Binance Pay (estado: webhook real en views_webhooks.py; draft eliminado de payment_views.py)

- `BinanceWebhookView` draft (referencias a metodos inexistentes) eliminado de `apps/finance/views/payment_views.py` (v1.1.0, commit 05ee7b8).
- `POST /finance/webhooks/binance/` -> `BinanceWebhookView` en `apps/finance/views/views_webhooks.py` con verificacion HMAC-SHA256.
- Fail-closed: 503 si `BINANCE_WEBHOOK_SECRET` falta, 401 si firma invalida. Sin bypass DEBUG.
- Tests: 6 casos en `tests/test_webhooks_hardening.py` (`TestBinanceWebhookFailClosed`).

---

## 2. GLOSARIO DE DOMINIO

| Termino | Definicion |
|---|---|
| **Fee de agencia** | Comision que cobra la agencia sobre el precio del proveedor. Campo `fee_agencia_interno` en `ItemVenta` (`apps/bookings/models/venta.py:539`). |
| **Boleto de tercero / BoletoImportado** | Boleto aereo emitido por un GDS/consolidador e importado al sistema (PDF o TXT). Modelo `BoletoImportado` en `apps/bookings/models/venta.py`. |
| **Diferencial cambiario** | Ganancia/perdida por diferencia entre tasa BCV oficial y tasa del mercado paralelo (VES). Se refleja en `PagoVenta.monto_igtf` y totales de `Factura` en doble moneda (USD/VES). |
| **IGTF** | Impuesto a los Grandes Transacciones Financieras (3% Venezuela). Se calcula automaticamente en `PagoVenta` cuando `aplica_igtf=True`. |
| **GDS** | Global Distribution System (Sabre, Amadeus, KIU, Copa SPRK). Sistemas de reserva aerea. |
| **PNR** | Passenger Name Record — Codigo alfanumerico de 6 caracteres de reserva en un GDS (ej: ABC123). |
| **IVA (VEN-NIF)** | IVA venezolano (16% general, 25% suntuario/turismo). Tasa default en `AgenciaConfiguracion.iva_por_defecto`. |
| **VEN-NIF** | Regimen fiscal venezolano de facturacion electronica (libro de ventas, IVA, ISLR). |
| **Retencion ISLR** | Retencion de Impuesto Sobre La Renta (5% sobre comisiones). Modelo `RetencionISLR` en `apps/finance/models_stubs.py`. |
| **Consolidador** | Mayorista que consolida boletos de multiples aerolineas y emite factura unica a la agencia. |
| **Conciliacion / SLOT** | Proceso de matching entre boleto emitido y asiento contable/consolidador. Modelo `ConciliacionBoleto`. |
| **LC (Linea de Credito)** | Credito que el consolidador otorga a la agencia. [VERIFICAR — modelo LineaCreditoProveedor asumido, no leido directamente]. |
| **FOID** | Form of Identification — campo que contiene documento de identidad del pasajero en boletos GDS (ej: IDPP123456). |
| **Tarifario** | Catalogo de precios de hoteles o paquetes. Modelo `HotelTarifario` (apps/bookings/). |
| **IATA Office ID** | Codigo alfanumerico de 8-9 caracteres que identifica la oficina emisora de un boleto (ej: BLA005RSJ, CCS00ESKA). |

---

## 3. STACK TECNOLOGICO EXACTO

| Componente | Version / Detalle | Verificado en |
|---|---|---|
| **Python** | 3.13 (target-version = "py313") | .ruff.toml |
| **Django** | 5.2.x (migracion 0051+ aplicada) | core/migrations/0051_api_keys_pbkdf2.py |
| **DRF** | djangorestframework | base.py |
| **Base de datos** | PostgreSQL 15 | docker-compose.yml service travelhub_db |
| **Redis** | 3 instancias: redis-cache, redis-celery, redis-evolution | docker-compose.yml + base.py |
| **Frontend** | HTMX + Alpine.js + Tailwind CSS + Unfold Admin | base.py INSTALLED_APPS + settings_unfold.py |
| **Celery** | django_celery_results + django_celery_beat | base.py + travelhub/celery_beat_schedule.py |
| **Stripe** | Python stripe library | base.py STRIPE_SECRET_KEY |
| **Evolution API** (WhatsApp) | Servicio externo http://evolution:8080 | base.py WHATSAPP_MICROSERVICE_URL |
| **Gemini** (AI core) | google-genai; gemini-1.5-flash (default), gemini-1.5-pro (razonamiento) | apps/automation/services/ai_engine.py:70-74 |
| **Sentry** | sentry-sdk con integraciones Django+Celery+Redis | production.py |
| **drf-spectacular** | OpenAPI 3.0 / Swagger / ReDoc | base.py SPECTACULAR_SETTINGS |
| **Cloudflare R2** | Almacenamiento S3-compatible para archivos | base.py USE_R2, AWS_* vars |
| **django-axes** | Proteccion fuerza bruta (5 intentos, 1h cooloff) | base.py AXES_* |
| **Fernet (cryptography)** | Cifrado simetrico en reposo (ENCRYPTION_KEY) | core/fields.py |
| **WeasyPrint** | Generacion de PDFs de boletos (sincrono) | ticket_parser_service.py:_generate_pdf_sync |
| **Gotenberg** | Generacion de PDFs via container (alternativa) | ANALISIS_BRECHA_VS_PLAN.md |
| **Whitenoise** | Servir estaticos en produccion | base.py MIDDLEWARE |
| **django-cors-headers** | CORS management | base.py |
| **Waffle** | Feature flags | base.py INSTALLED_APPS |
| **Xero SDK** | Integracion contabilidad (298 lineas) | ANALISIS_BRECHA_VS_PLAN.md |
| **Amadeus SDK** | Parser PNR + service | apps/automation/services/amadeus_service.py |
| **django-prometheus** | Metricas Prometheus en /prometheus/ | travelhub/urls.py:107 |
| **PWA manual** | manifest.json + service-worker.js con rutas conectadas | travelhub/urls.py:116-118, core/views/pwa_views.py |
| **SSO (OIDC/SAML)** | Implementacion custom — sin libreria externa verificada | core/sso/models.py, core/sso/views.py |
| **GitHub Actions CI** | .github/workflows/ci.yml (gitleaks, mypy, bandit, pip-audit) | CHANGELOG.md v1.1.0 |

### Variables de entorno obligatorias

Definidas en `.env.example`. **Nunca** commitear `.env` ni `.env.local`.

| Variable | Proposito |
|---|---|
| SECRET_KEY | Clave secreta Django (session signing, CSRF) |
| DATABASE_URL | Connection string PostgreSQL |
| ENCRYPTION_KEY | Clave Fernet en base64 (32+ chars) para EncryptedCharField |
| CELERY_BROKER_URL | Redis para tareas Celery asincronas |
| REDIS_URL | Redis para cache de Django |
| GEMINI_API_KEY | API key global de Google Gemini (puede sobreescribirse por agencia) |
| STRIPE_SECRET_KEY | Stripe API key (modo live en prod) |
| STRIPE_PUBLISHABLE_KEY | Stripe clave publica para frontend |
| STRIPE_WEBHOOK_SECRET | Verificacion de firma Stripe — OBLIGATORIA, fail-closed |
| BINANCE_WEBHOOK_SECRET | Verificacion HMAC-SHA256 Binance — OBLIGATORIA, fail-closed |
| TELEGRAM_WEBHOOK_SECRET | Verificacion timing-safe Telegram — OBLIGATORIA, fail-closed |
| WHATSAPP_MICROSERVICE_URL | URL de Evolution API (WhatsApp) |
| SENTRY_DSN | Error tracking (opcional en dev) |
| JWT_SIGNING_KEY | Clave independiente para JWT (default: SECRET_KEY si no se define) |

---

## 4. INFRAESTRUCTURA Y DEPLOY

**Produccion:** Render (Docker), dominio `travelhub.cc`, PostgreSQL 15, Redis 3 instancias, Traefik reverse proxy (traefik_data/), Cloudflare R2 para assets estaticos y media.

**CI/CD:** GitHub Actions — `.github/workflows/ci.yml` (confirmado en CHANGELOG v1.1.0):
- Job `secret-scan`: gitleaks-action@v2 con fetch-depth: 0 (historial completo).
- Job `lint`: ruff + mypy --ignore-missing-imports (con django-stubs).
- Job `security-scan`: bandit -r apps/ core/ + pip-audit (sin `|| true` — falla el build).
- Coverage threshold: --cov-fail-under=75.
- Deploy en Render se dispara post-merge (mecanismo exacto: [VERIFICAR — no se leyo render.yaml]).

**K8s:** Manifiestos Helm en `k8s/` — [VERIFICAR — no se leyo si estan activos en produccion].

**Pre-commit:** `.pre-commit-config.yaml` con detect-private-key, end-of-file-fixer, trailing-whitespace, check-yaml, check-toml, check-merge-conflict, check-added-large-files.

**Desarrollo local (desde cero):**

```bash
git clone <repo> && cd travelhub_project
cp .env.example .env.local
# Editar .env.local con los secretos reales
docker compose up -d
docker exec travelhub_web python manage.py migrate
docker exec -it travelhub_web python manage.py createsuperuser
docker exec travelhub_web python manage.py loaddata fixtures/initial_data.json
open http://localhost:8000
```

**Settings auto-routing:** `travelhub/settings/__init__.py` lee DJANGO_ENV -> carga development.py, production.py o testing.py. Default: development.

---

## 5. MAPA DE ARCHIVOS CRITICOS

```
travelhub/                              # Paquete de configuracion Django
+-- settings/
|   +-- __init__.py                     # Auto-router: DJANGO_ENV -> archivo de settings
|   +-- base.py                         # ~771 lineas — config base compartida
|   +-- development.py                  # DEBUG=True, email console, AXES_ENABLED override
|   +-- production.py                   # HSTS, Sentry, SECURE_PROXY_SSL_HEADER
|   +-- testing.py                      # Celery EAGER, cache local, sin R2
+-- settings.py                         # Shim de compatibilidad (1226 bytes)
+-- urls.py                             # 148 lineas — enrutador maestro
+-- urls_api.py                         # 48 lineas — router DRF fusionado
+-- celery.py                           # App Celery (4310 bytes)
+-- celery_beat_schedule.py             # Tareas programadas periodicas

core/                                   # App central — multi-tenancy, seguridad, modelos base
+-- middleware.py                       # 521 lineas — ThreadLocalContextMiddleware (RLS)
|                                       #   SecurityHeadersMiddleware (CSP+nonce)
|                                       #   system_context(), agency_context()
+-- middleware_saas.py                  # SaaSLimitMiddleware — bloqueo por cuotas SaaS
+-- middleware_onboarding.py            # OnboardingRedirectMiddleware
+-- middleware_ai_ratelimit.py          # AIRateLimitMiddleware — throttle de IA
+-- middleware_performance.py           # QueryCountDebugMiddleware, CacheHeaderMiddleware
+-- middleware_plan_limits.py           # [VERIFICAR — coexiste con middleware_saas.py]
+-- security.py                         # 229 lineas — get_agencia_or_403,
|                                       #   get_object_tenant_or_404,
|                                       #   filter_queryset_by_tenant,
|                                       #   get_user_active_agency (cache Redis)
+-- fields.py                           # EncryptedCharField, EncryptedTextField (Fernet)
+-- validators.py                       # antivirus_hook (ClamAV), sanitize_html (bleach)
+-- permissions.py                      # IsStaffOrGroupWrite, rol_requerido()
+-- throttling.py                       # AgenciaAIParserThrottle (20/min, 200/dia)
+-- signals.py                          # Senales core (parseo boletos, WhatsApp on_commit)
+-- signals_audit.py                    # Senales de auditoria con hash chain
+-- signals_bypass.py                   # disable_signals() context manager con stack trace
+-- api_registry.py                     # 20469 bytes — registro central de API
+-- api/
|   +-- mixins/tenant.py                # 39 lineas — TenantViewSetMixin (DRF)
|   +-- mixins/saas_mixin.py            # 378 lineas — SaaSMixin (CBV Django + RBAC)
|   +-- public_auth.py                  # 106 lineas — APIKeyAuthentication, HasAPIKeyScope
+-- models/
|   +-- base.py                         # 291 lineas — AgenciaMixin, AgenciaManager,
|   |                                   #   SoftDeleteModel, GlobalAwareAgenciaManager
|   +-- agencia.py                      # 556 lineas — Agencia, AgenciaBranding,
|   |                                   #   AgenciaConfiguracion, UsuarioAgencia
|   +-- cron_api_key.py                 # CronApiKey — PBKDF2-HMAC-SHA256 (600K iter)
|   |                                   #   + lookup_hash SHA-256 para O(1) lookup
|   +-- api_keys.py                     # DEPRECATED — tabla eliminada (migracion 0049)
|   |                                   #   Modelo Python sin backing table
|   +-- audit.py                        # AuditLog con hash chain
|   +-- ai.py                           # AIUsageLog — log de cada llamada a Gemini
|   +-- aeropuerto.py                   # Aeropuerto (catalogo global)
|   +-- feature_flags.py                # FeatureFlag (Waffle)
|   +-- magic_link.py                   # MagicLinkToken
|   +-- historial_boletos.py            # AnulacionBoleto, HistorialCambioBoleto
+-- sso/
|   +-- models.py                       # SSOProvider — Azure AD, Okta OIDC/SAML,
|   |                                   #   Google Workspace, Generic OIDC/SAML
|   +-- views.py                        # sso_login, sso_callback (12215 bytes)
+-- views/
|   +-- cron_views.py                   # 5 endpoints cron (BCV sync, reminders, cierre)
|   +-- auth_views.py                   # MagicLinkRequestView, MagicLinkVerifyView, TokenLogoutView
|   +-- pwa_views.py                    # manifest(), service_worker(), offline()
|   +-- status_views.py                 # status_page, status_api (solo staff)
|   +-- marketing_views.py              # public_landing, public_pricing
|   +-- docs_views.py                   # docs_index, docs_page, public_manual
+-- management/commands/
    +-- rotate_encryption_key.py        # Rotacion de ENCRYPTION_KEY en batches
    +-- generate_cron_key.py            # Generar CronApiKey desde CLI
    +-- setup_production.py             # Setup inicial de produccion

apps/
+-- automation/                         # Core de IA — parser, agente, copywriter
|   +-- services/
|   |   +-- ai_engine.py                # 632 lineas — AIEngine (clase central Gemini)
|   |   |                               #   DEFAULT_MODEL="gemini-1.5-flash"
|   |   |                               #   PRO_MODEL="gemini-1.5-pro"
|   |   |                               #   get_gemini_api_key() resuelve por agencia o global
|   |   +-- ai_agent.py                 # TravelHubAgent — 19 herramientas Gemini function calling
|   |   +-- ai_copywriter.py            # AICopywriter — captions Instagram para hoteles
|   |   +-- ticket_parser_service.py    # 886 lineas — orquestador principal de parseo
|   |   |                               #   _generate_pdf_sync (WeasyPrint)
|   |   |                               #   _is_celery_available() para PDF sync vs async
|   |   +-- ai_tools.py                 # 891 lineas — AgentTools (19 funciones del agente)
|   |   +-- ai_router.py                # Router de IA — decide que modelo usar
|   |   +-- venta_automation.py         # VentaAutomationService
|   |   +-- amadeus_service.py          # Parser PNR Amadeus
|   |   +-- linkeo_service.py           # Servicio de linkeo de boletos
|   |   +-- hotel_parser_service.py     # Parser de tarifarios de hoteles
|   +-- parsers/
|       +-- ai_universal_parser.py      # 356 lineas — UniversalAIParser (GOD MODE)
|       |                               #   SYSTEM_PROMPT 13 reglas estrictas
|       |                               #   Sabre, Amadeus, KIU, Copa SPRK,
|       |                               #   Estelar Web, Rutaca Web, Avior, Wingo
|       +-- gemini_parser.py            # 187 lineas — GeminiParser (BaseTicketParser)
|       +-- kiu_parser.py               # Parser regex KIU (28643 bytes)
|       +-- base_parser.py              # BaseTicketParser, ParsedTicketData (29853 bytes)
|       +-- ticket_parser.py            # extract_data_from_text — entrada publica
|       +-- extraction.py               # ExtractionService
|       +-- normalization.py            # DataNormalizationService
|       +-- pdf_generation.py           # PdfGenerationService
|       +-- persistence.py              # BoletoPersistenceService
|       +-- registry.py                 # Registro de parsers disponibles
+-- bookings/
|   +-- models/
|   |   +-- venta.py                    # 718 lineas — Venta, ItemVenta, BoletoImportado,
|   |   |                               #   FeeVenta, PagoVenta, VentaAuditFinding
|   |   +-- servicios.py                # ProductoServicio (TipoProductoChoices)
|   |   +-- proveedores.py              # Proveedor
|   +-- urls.py                         # 299 lineas
+-- finance/
|   +-- models.py                       # Factura (AgenciaMixin, sin SoftDelete),
|   |                                   #   ItemFactura, Pago, FiscalConfig
|   +-- models_stubs.py                 # 682 lineas — stubs legacy (managed=False):
|   |                                   #   FacturaConsolidada, RetencionISLR,
|   |                                   #   TaxRefundOpportunity, LinkDePago,
|   |                                   #   ConciliacionBoleto, GastoOperativo,
|   |                                   #   ReporteReconciliacion
|   +-- models_pg.py                    # Modelos con raw SQL / PG views
|   +-- services/
|   |   +-- facturacion_service.py      # FacturacionService.generar_factura_desde_venta()
|   |   +-- factura_service.py          # FacturaService
|   +-- urls.py                         # 232 lineas — router finanzas + webhooks
+-- crm/                                # Clientes, pasajeros, WhatsApp
+-- contabilidad/
|   +-- models.py                       # CuentaContable, AsientoContable,
|                                       #   MovimientoContable, PlanContable, DetalleAsiento
+-- communications/
|   +-- services/evolution_api_service.py  # Evolution API (WhatsApp)
+-- cotizaciones/                       # Cotizaciones + AI Magic-GPT
+-- marketing/                          # Automatizacion de marketing
+-- cms/                                # Content Management
+-- common/
    +-- services/
    |   +-- saas_quota_service.py       # SaaSQuotaService.check_quota()
    |   +-- bi_service.py               # Business Intelligence KPIs
    |   +-- catalog_service.py          # CatalogNormalizationService (airports_master.json)
    |   +-- circuit_breaker.py          # Circuit Breaker para tareas Celery
    +-- models.py                       # Pais, Ciudad, Aerolinea, Moneda, UserProgress
```

---

## 6. LOGICA DE MULTI-TENANCY (4 CAPAS DE DEFENSA)

### Capa 1: AgenciaManager.get_queryset() — core/models/base.py:50

Manager por defecto de todos los modelos que heredan `AgenciaMixin`. Aplica 3 filtros en orden:

1. **Soft delete:** si el modelo tiene `is_deleted`, filtra `is_deleted=False`.
2. **System context bypass:** si `is_system_context()` retorna True, retorna el queryset sin filtro.
3. **Multi-tenancy** segun `agency_var` (ContextVar del middleware):
   - **Caso A** (agencia activa): `queryset.filter(agencia=agencia)` — solo registros de esa agencia.
   - **Caso B** (superuser sin agencia): devuelve todo (God Mode global).
   - **Caso C** (pytest / manage.py): sin filtro (detectado via sys.argv — ver bug P2-006).
   - **Caso D** (usuario normal sin agencia): `queryset.none()` — falla cerrada.

### Capa 2: TenantViewSetMixin — core/api/mixins/tenant.py

Para DRF ViewSets. Sobrescribe `get_queryset()` (filtrado por agencia) y `perform_create()` (asigna agencia). Superusuarios hacen bypass.

### Capa 3: SaaSMixin — core/api/mixins/saas_mixin.py

Para Django Class-Based Views. Similar a TenantViewSetMixin + verificacion de roles RBAC (admin, gerente, vendedor, contador, consulta).

### Capa 4: Helpers de seguridad — core/security.py

- `get_agencia_or_403(request)` — extrae agencia del request, 403 si no tiene.
- `get_object_tenant_or_404(model, agencia, **kwargs)` — get_object_or_404 con filtro de agencia.
- `filter_queryset_by_tenant(queryset, agencia)` — filtra queryset por agencia.
- `get_user_active_agency(user)` — obtiene agencia activa con cache Redis (TTL original 120s, bug P1-004 propone reducir a 30s).

### Middleware RLS en PostgreSQL

`ThreadLocalContextMiddleware` (`core/middleware.py:137`) al inicio de cada request:

```sql
SET LOCAL app.current_agencia_id = '<uuid>';
SET LOCAL app.bypass_rls = 'true'|'false';
-- Al final: purgadas automaticamente al commit/rollback (ATOMIC_REQUESTS=True)
```

Riesgo critico documentado: Si se usa PgBouncer en modo transaction con CONN_MAX_AGE > 0, las variables SET LOCAL pueden escapar de la transaccion (ver bug P1-003).

### Context managers — core/middleware.py:55-103

```python
@contextmanager
def system_context(reason: str = "unspecified", max_seconds: float = 60.0):
    # Deshabilita TODOS los filtros de tenant
    # Logea: [SYSTEM_CONTEXT OPEN] reason=... caller=<module:lineno>
    # Alerta con error si dura > max_seconds
    # Token-based reset garantizado en finally

@contextmanager
def agency_context(agency, reason: str = "unspecified"):
    # Establece manualmente el contexto de la agencia
    # Para tareas Celery donde no hay request
```

### Modelos que heredan AgenciaMixin

Todos en apps/: Venta, ItemVenta, Factura, BoletoImportado, ProductoServicio, Cliente, CuentaContable, etc.

`SoftDeleteModel` anade: is_deleted, deleted_at, with_deleted manager, delete() (logico), hard_delete() (fisico), restore().

### Modelos GLOBALES (sin AgenciaMixin)

FeatureFlag, AuditLog, plantillas de notificacion. Usan `GlobalAwareAgenciaManager` (base.py:95) que expone registros con `agencia__isnull=True` (plantillas globales) junto con los de la agencia activa.

---

## 7. ARQUITECTURA DE LA IA INTERNA

### 7.1 Motor Central — AIEngine (apps/automation/services/ai_engine.py)

```python
class AIEngine:
    DEFAULT_MODEL  = "gemini-1.5-flash"   # Parseo rapido y copywriting
    PRO_MODEL      = "gemini-1.5-pro"     # Razonamiento complejo
    VISION_MODEL   = "gemini-1.5-flash"   # Analisis de imagenes/PDFs
    FALLBACK_MODEL = "gemini-1.5-flash"   # Si el modelo principal falla
```

Resolucion de API key (`get_gemini_api_key(agency=None)`):
1. Busca en `AgenciaConfiguracion.gemini_api_key` (API key por agencia — enterprise).
2. Fallback: `os.environ["GEMINI_API_KEY"]` o `settings.GEMINI_API_KEY` (global).

Excepciones custom: CircuitBreakerException, QuotaExhaustedException (HTTP 429), GeminiConfigurationError.

Rate limiting: AgenciaAIParserThrottle — 20 req/min, 200 req/dia por agencia.

Logging: AIUsageLog (core/models/ai.py) registra cada llamada (modelo, tokens, tiempo, costo estimado).

---

### 7.2 Ticket Parser Pro — Flujo completo

Orquestador: ticket_parser_service.py (886 lineas, apps/automation/services/).

Estrategia dual (AI-first + Regex fallback):

```
PDF/TXT input -> ExtractionService.extract_text()
     |
     +---> UniversalAIParser.parse()      <- PRIMERO (GOD MODE, Gemini)
     |          | Falla / texto < 50 chars
     |          v
     +---> GeminiParser / KiuParser / Regex parsers  <- FALLBACK
               |
               v
         DataNormalizationService.normalize_ticket_data()
               |
               v
         PdfGenerationService (WeasyPrint sincrono / Celery async si disponible)
               |
               v
         BoletoPersistenceService.save_to_db()
               |
               v
         BoletoImportado (DB) -> estado_parseo: OK/ERR/PEN
```

UniversalAIParser (apps/automation/parsers/ai_universal_parser.py):
- SYSTEM_PROMPT de 13 reglas estrictas de extraccion ("GOD MODE").
- Soporta: Sabre, Amadeus, KIU, Copa SPRK, Estelar Web, Rutaca Web, Avior, Wingo.
- Detecta prorrateo multi-pasajero y separa en boletos individuales.
- ATENCION: Trunca texto a 15,000 chars silenciosamente (bug P1-006 — pendiente).

GeminiParser (apps/automation/parsers/gemini_parser.py):
- Prompt de 13+ reglas detalladas con ejemplos GDS.
- can_parse(text): retorna True si len(text) > 50.

KiuParser (apps/automation/parsers/kiu_parser.py):
- 28,643 bytes — parser regex especializado en boletos KIU/Avior/Rutaca.

PDF sync vs async:
```python
def _is_celery_available() -> bool:
    """Hace ping a Redis; si falla -> PDF se genera sincronamente con WeasyPrint."""
```

---

### 7.3 TravelHub Agent — TravelHubAgent (apps/automation/services/ai_agent.py)

Agente ERP completo con Gemini Function Calling automatico (max. 10 llamadas remotas por query).

19 herramientas disponibles (clase AgentTools en ai_tools.py):
- get_sales_stats(days) — estadisticas de ventas por periodo
- get_financial_kpis() — KPIs rapidos P&L
- get_pending_payments() — pagos pendientes
- get_financial_report() — reporte financiero completo
- get_client_info() — info de clientes del CRM
- get_quote_status() — estado de cotizaciones
- get_recent_expenses() — gastos operativos
- generate_cms_content() — articulos de blog en Markdown
- list_cms_content() — listado de contenido CMS
- get_reconciliation_summary() — resumen de conciliacion
- get_reconciliation_discrepancies() — discrepancias de conciliacion
- get_cash_flow_summary() — flujo de caja actual
- get_cashflow_forecast() — proyeccion 30 dias
- get_account_balance() — saldo de cuenta contable
- generate_marketing_copy() — copy de marketing para hoteles
- encode_iata_location(city) — ciudad -> codigo IATA
- decode_iata_code(code) — codigo IATA -> detalles aeropuerto
- find_nearest_airports(lat, lon) — aeropuertos cercanos a coordenadas
- get_travel_requirements(origin, dest) — visa, pasaporte, vacunas

Acceso a datos: Todas las herramientas usan `get_current_agency()` del middleware — datos 100% aislados por tenant.

Manejo de errores: try/except Exception devuelve string descriptivo al usuario sin exponer tracebacks.

---

### 7.4 AI Copywriter — AICopywriter (apps/automation/services/ai_copywriter.py)

- Genera captions de Instagram para hoteles del catalogo (HotelTarifario).
- Usa ai_engine.call_gemini(prompt) con tono: PROFESIONAL_AVENTURERO, FORMAL, AVENTURERO, ROMANTICO.
- Fallback: string de error descriptivo si ai_engine.is_ready es False.

---

## 8. CONTRATO DE API / ENDPOINTS PRINCIPALES

### Autenticacion y acceso

| Metodo | Ruta | Proposito | Auth |
|---|---|---|---|
| POST | /api/auth/jwt/obtain/ | Obtener JWT (access + refresh) | Publico |
| POST | /api/auth/jwt/logout/ | Invalidar refresh token | JWT |
| GET | /auth/magic-request/ | Solicitar magic link por email | Publico |
| GET | /auth/magic/<token>/ | Verificar magic link -> sesion | Publico |
| GET | /sso/login/<provider_id>/ | Iniciar SSO (OIDC/SAML) | Publico |
| GET | /sso/callback/<provider_id>/ | Callback SSO | Publico |

### Sistema e infraestructura

| Metodo | Ruta | Proposito | Auth |
|---|---|---|---|
| GET | /health/ | Health check del sistema | Publico |
| GET | /health/metrics/ | Metricas para monitoreo | Publico |
| GET | /prometheus/ | Metricas Prometheus | Publico |
| GET | /api/schema/ | OpenAPI schema JSON | Staff (prod) |
| GET | /api/docs/ | Swagger UI | Staff (prod) |
| GET | /api/redoc/ | ReDoc UI | Staff (prod) |
| GET | /csp-report/ | Receptor de violaciones CSP | Publico |
| GET | /status/ | Status page del sistema | Staff |
| GET | /manifest.json | PWA manifest | Publico |
| GET | /service-worker.js | PWA service worker | Publico |

### Cron endpoints (protegidos con CronApiKey)

| Metodo | Ruta | Proposito | Auth |
|---|---|---|---|
| GET/POST | /system/api/cron/sincronizar-bcv/ | Sync tasa BCV | CronApiKey |
| GET/POST | /system/api/cron/recordatorios-pago/ | Recordatorios de pago | CronApiKey |
| GET/POST | /system/api/cron/cierre-mensual/ | Cierre contable mensual | CronApiKey |

### Bookings (Reservas)

| Metodo | Ruta | Proposito | Auth |
|---|---|---|---|
| GET/POST | /api/proveedores/ | CRUD proveedores | Session/Token |
| GET/POST | /api/productoservicio/ | CRUD productos/servicios | Session/Token |
| GET/POST | /api/ventas/ | CRUD ventas | Session/Token |
| GET | /api/boletos/buscar/ | Busqueda de boletos importados | Session/Token |
| POST | /api/boletos/upload/ | Upload boleto (PDF/TXT) | Session/Token |
| POST | /api/boletos/<id>/reintentar-parseo/ | Reintentar parsing IA | Session/Token |
| POST | /api/boletos/<id>/crear-venta/ | Crear Venta desde boleto | Session/Token |

### Finance

| Metodo | Ruta | Proposito | Auth |
|---|---|---|---|
| GET/POST | /api/facturas/ | CRUD facturas | Session/Token |
| GET | /api/billing/plans/ | Listar planes SaaS + precios | Session/Token |
| POST | /api/billing/checkout/ | Crear sesion Stripe checkout | Session/Token |
| POST | /api/billing/portal/ | Stripe customer portal | Session/Token |
| POST | /api/billing/change-plan/ | Cambiar plan | Session/Token |
| POST | /api/billing/preview-change/ | Preview de cambio de plan | Session/Token |
| POST | /api/billing/downgrade-free/ | Downgrade a plan FREE | Session/Token |
| POST | /finance/webhooks/stripe/ | Webhook Stripe (sin CSRF) | Publico (firma Stripe) |
| POST | /finance/webhooks/binance/ | Webhook Binance Pay | Publico (HMAC-SHA256) |

### CRM y Comunicaciones

| Metodo | Ruta | Proposito | Auth |
|---|---|---|---|
| GET/POST | /api/clientes/ | CRUD clientes | Session/Token |
| GET/POST | /api/pasajeros/ | CRUD pasajeros | Session/Token |
| POST | /crm/webhook/whatsapp/ | Webhook WhatsApp entrante | Publico (firma) |
| POST | /crm/webhook/evolution/ | Webhook Evolution API | Publico (firma) |
| POST | /api/push/subscribe/ | Suscribir a push notifications | Session/Token |
| POST | /api/push/unsubscribe/ | Desuscribirse de push | Session/Token |
| POST | /i18n/set_language/ | Cambiar idioma de sesion | Session |
| GET/POST | /api/audit-logs/ | Logs de auditoria | Session/Token (staff) |

---

## 9. SEGURIDAD Y REGLAS DE ORO

### Medidas implementadas y verificadas

1. **Cifrado Fernet** (core/fields.py): EncryptedCharField/EncryptedTextField cifran en reposo con ENCRYPTION_KEY. Detecta doble cifrado (no recifra si empieza con gAAAAA). _decrypt() reporta a Sentry y lanza ValueError.

2. **CronApiKey con PBKDF2:** core/models/cron_api_key.py — pbkdf2_hmac("sha256", 600_000 iteraciones). lookup_hash (SHA-256) para O(1) lookup. Backward-compat con keys legacy SHA256 via _verify_key().
   ATENCION: APIKey en core/models/api_keys.py es dead code — tabla eliminada (migracion 0049). Modelo Python existe sin backing table. Marcado DEPRECATED. Aun importado en 5 archivos por atributos que CronApiKey no soporta (rate_limit, plan, scopes, user).

3. **Anti-fuerza bruta (django-axes):** 5 intentos fallidos, 1h cooloff, por username+IP. AXES_ENABLED=True default en dev, override con AXES_ENABLED_DEV=false.

4. **Row-Level Security (RLS):** SET LOCAL app.current_agencia_id al inicio de cada request. ATOMIC_REQUESTS=True garantiza purga automatica al final.

5. **CSP con nonces por request:** SecurityHeadersMiddleware inyecta CSP con nonce. Sin unsafe-eval globalmente. Excepcion: /admin/ y /system/ tienen unsafe-eval para Alpine.js (pendiente migrar a @alpinejs/csp-bundle).

6. **Webhooks fail-closed (v1.1.0):**
   - Stripe: stripe.Webhook.construct_event() obligatorio. 503/401 si falla.
   - Binance: HMAC-SHA256 obligatorio. 503/401 si falla.
   - Telegram: hmac.compare_digest timing-safe. 403 si falta o invalido.
   - Test anti-regresion: test_bypass_debug_no_esta_en_views_webhooks verifica que la cadena "DEBUG" no este en views_webhooks.py.

7. **Validacion de archivos** (core/validators.py): Extensiones permitidas, magic bytes, ClamAV (try/except fallback), sanitizacion de filename, limites por plan.

8. **Sanitizacion HTML:** sanitize_html() usa bleach con whitelist. Fallback seguro: strip_tags() si bleach no instalado.

9. **JWT signing key separada:** JWT_SIGNING_KEY (default SECRET_KEY). Separada para limitar impacto si SECRET_KEY se compromete.

10. **God Mode timeout:** system_context() alerta si dura mas de 60s. Superusuarios impersonando agencia tienen timeout de sesion adicional.

11. **Proteccion IDOR:** get_object_tenant_or_404() debe usarse en toda vista funcional. ATENCION: BoletoRetryParseAPIView y VentaDoubleInvoiceAPIView tienen IDOR pendiente (bugs P0-002, P0-003).

12. **SSO/SAML por agencia:** SSOProvider model en core/sso/models.py — cada agencia puede configurar Azure AD, Okta OIDC/SAML, Google Workspace o Generic OIDC/SAML. auto_provision=True crea usuario automaticamente si no existe.

### Reglas del Repositorio (NUNCA violar)

1. No inventar librerias. Toda libreria debe estar en requirements/ e INSTALLED_APPS.
2. Validar en modelos. AgenciaMixin.save() valida cruce de datos.
3. No saltarse el filtro de agencia. No usar .all_objects en vistas de usuario sin justificacion.
4. Usar system_context() con reason obligatoria. Logea stack trace. Alerta si dura > 60s.
5. No exponer secretos. ENCRYPTION_KEY, SECRET_KEY, JWT_SIGNING_KEY solo en .env.local.
6. Backward compatibility de hashes. _verify_key() soporta PBKDF2 y SHA256 legacy.
7. No romper atomic_requests. Endpoints publicos (health): @transaction.non_atomic_requests.
8. Nunca anadir bypass if DEBUG a verificacion de webhooks. Test anti-regresion en CI.
9. No exponer str(e) en respuestas 500. Usar error_id + logger.exception() (ver bug P0-006).

---

## 10. BUGS Y LIMITACIONES CONOCIDAS (deuda tecnica, no en trabajo activo)

### Seguridad (P0) — Criticos sin sprint activo

| ID | Descripcion | Archivo | Impacto |
|---|---|---|---|
| P0-002 | BoletoRetryParseAPIView: IDOR — .get(pk=pk) sin validar tenant | apps/bookings/views/boleto_views.py:159 | Cross-tenant data exposure (OWASP A01) |
| P0-003 | VentaDoubleInvoiceAPIView: Venta.objects.get(pk=pk) sin assert de tenant | apps/bookings/views/boleto_views.py:349 | IDOR — Cross-tenant access |
| P0-006 | BoletoUploadAPIView: return Response error str(e) expone tracebacks | apps/bookings/views/boleto_views.py:126-129 | Information Disclosure (OWASP A09) |

### Estabilidad (P1)

| ID | Descripcion | Impacto |
|---|---|---|
| P1-001 | Doble signal post_save en BoletoImportado — posible doble parseo/doble billing Gemini | Double billing, race condition en estado_parseo |
| P1-002 | celery.py llama django.setup() explicitamente — puede crashear tests | Inestabilidad en CI |
| P1-003 | CONN_MAX_AGE=600 + PgBouncer en modo transaction — fuga RLS cross-tenant | CRITICO si se usa PgBouncer; USE_PGBOUNCER=false en .env.production actual |
| P1-004 | Cache de agencia TTL=120s — acceso 2min post-desactivacion de agencia | Ventana de seguridad si agencia comprometida |
| P1-005 | locale.setlocale monkey patch global en modulo importado | Afecta todas las librerias que usen locale |
| P1-006 | UniversalAIParser trunca texto a 15,000 chars silenciosamente | Parseo incorrecto de boletos grandes sin aviso |
| P1-007 | _send_factura_whatsapp puede ejecutar .apply() sincrono en on_commit | Datos inconsistentes si broker caido |

### Calidad de codigo (P2)

| ID | Descripcion |
|---|---|
| P2-002 | Archivos de debug en raiz (debug_celery_tasks.py, etc.) — credenciales potenciales |
| P2-004 | celery.py usa settings.production como default en desarrollo |
| P2-005 | Mapa de meses GDS definido 4 veces (normalization.py + 3x en ai_schemas.py) |
| P2-006 | AgenciaManager.get_queryset() parsea sys.argv en cada query (overhead por request) |

### Modelos stub / dead code conocidos

| Modelo | Estado | Ubicacion |
|---|---|---|
| FacturaFiscal | managed=False, tabla no existe en prod | apps/finance/models_stubs.py |
| APIKey | DEPRECATED, tabla eliminada (migracion 0049) | core/models/api_keys.py |
| FacturaConsolidada | Stub legacy solo para tests | apps/finance/models_stubs.py |

### Integraciones incompletas

- PWA: manifest.json y service-worker.js con rutas conectadas en urls.py. Cache offline [VERIFICAR — no se leyo pwa_views.py completo].
- i18n: LANGUAGES = [("es", "Espanol"), ("en", "English")]. Espanol: 42 entradas; ingles: 332 entradas. Variantes regionales no implementadas.
- SSO: Modelo y views existen (core/sso/). Integracion con IdPs reales [VERIFICAR — no se leyo el flow completo de sso_callback].
- CSP unsafe-eval en admin: Alpine.js en Unfold admin requiere unsafe-eval en /admin/ y /system/. Pendiente migrar a @alpinejs/csp-bundle.

---

## 11. BRECHAS EN REPARACION (trabajo activo — rama hardening/operational-risks)

### Resueltas (Julio 2026)

| Brecha | Fix aplicado |
|---|---|
| Antivirus hook sin fallback | antivirus_hook() usa try/except, logea warning si ClamAV no disponible |
| Bleach fallback inseguro | sanitize_html() usa strip_tags() como fallback seguro |
| Decryption failure silencioso | _decrypt() lanza ValueError y reporta a Sentry |
| API keys con SHA256 raw | Migrado a PBKDF2-HMAC-SHA256 (600K iter + salt) + lookup_hash O(1) |
| Signal bypass sin auditoria | disable_signals() logea stack trace del caller |
| Axes deshabilitado en dev | AXES_ENABLED=True default en dev |
| JWT compartiendo SECRET_KEY | JWT_SIGNING_KEY variable independiente |
| Bandit deshabilitado en scripts | Eliminado "S" de per-file-ignores en .ruff.toml |
| Encryption key rotation | Nuevo comando rotate_encryption_key que re-cifra en batches |
| Tests xfail de contabilidad | Reescritos para usar campos reales de CuentaContable |
| Stripe flow incompleto | StripeWebhookView documentado — eventos, idempotencia, firma |
| Binance dead code | BinanceWebhookView draft y BinanceOrderCreateView sin ruta eliminados |
| APIKey dead code | DeprecationWarning en docstring de core/models/api_keys.py |
| Webhook DEBUG bypass | Sin if DEBUG en ningun webhook (test anti-regresion en CI) |
| CI/CD pipeline ausente | GitHub Actions con gitleaks, mypy, bandit, pip-audit (sin ||true) |
| Pre-commit hooks | detect-private-key, check-merge-conflict, check-added-large-files |
| system_context() sin timeout | max_seconds=60, stack trace del caller en audit logger |
| mypy sin adoption plan | 5 modulos con strict=True pasando sin errores |

### En progreso

- (ninguno actualmente en este sprint)

### Pendiente (priorizado)

| Brecha | Prioridad | Notas |
|---|---|---|
| P0-002: IDOR en BoletoRetryParseAPIView | P0 CRITICO | Correccion: usar get_object_tenant_or_404() |
| P0-003: IDOR en VentaDoubleInvoiceAPIView | P0 CRITICO | Misma correccion |
| P0-006: Traceback en respuestas 500 | P0 CRITICO | Usar error_id + logger.exception() |
| P1-001: Doble signal BoletoImportado | P1 ALTO | Consolidar en un unico receiver |
| P1-003: PgBouncer + CONN_MAX_AGE | P1 ALTO | Condicional USE_PGBOUNCER en prod settings |
| P1-004: Cache agencia TTL=120s | P1 ALTO | Reducir a 30s + signal de invalidacion |
| P1-006: Truncado silencioso 15K chars | P1 ALTO | Log warning + flag en resultado |
| P2-004: celery.py default settings.production | P2 MEDIO | Cambiar default a settings.development |
| PWA cache offline | P3 BAJO | Conectar service worker con estrategia de cache |
| i18n espanol | P3 BAJO | Completar de 42 a 300+ entradas .po |
| alpinejs/csp-bundle | P3 BAJO | Eliminar unsafe-eval de rutas admin |

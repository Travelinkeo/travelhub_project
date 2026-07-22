# CONTEXT_MAP.md — TravelHub SaaS

```
Última verificación contra código real: 2026-07-22
Rama/commit revisado: hardening/operational-risks @ e3abfa5
Verificado por: IA (Gemini 3.6 Flash / Antigravity)
Archivos leídos en esta sesión: travelhub/settings/base.py (783 líneas),
  core/models/base.py (281 líneas), core/middleware.py (538 líneas),
  core/security.py (230 líneas), core/fields.py (137 líneas),
  core/validators.py (209 líneas), core/throttling.py (77 líneas),
  core/signals.py (243 líneas), core/signals_audit.py (432 líneas),
  core/models/cron_api_key.py (125 líneas), core/models/agencia.py (576 líneas),
  apps/automation/services/ai_engine.py (632 líneas),
  apps/automation/parsers/ai_universal_parser.py (356 líneas),
  apps/automation/parsers/normalization.py (521 líneas),
  travelhub/urls.py (173 líneas), travelhub/urls_api.py (48 líneas),
  travelhub/celery.py (117 líneas), travelhub/celery_beat_schedule.py (116 líneas),
  docker-compose.yml (463 líneas), .env.example (137 líneas),
  CHANGELOG.md (65 líneas), TECH_DEBT_REMEDIATION.md (629 líneas),
  REMEDIATION_PLAN.md (516 líneas), locale/es/LC_MESSAGES/django.po (1191 líneas),
  compile_i18n.py (123 líneas)
```

---

## 1. PROPÓSITO DEL SISTEMA

TravelHub es un **CRM/ERP SaaS multi-tenant** para agencias de viajes venezolanas.
Gestiona el ciclo completo: cotización → venta → emisión de boletos aéreos (Sabre, Amadeus, KIU, Copa SPRK) → facturación VEN-NIF con doble moneda USD/VES → contabilidad → liquidación a proveedores.

**Modelo de negocio:** B2B. Las agencias pagan suscripción mensual (Stripe). Cada agencia tiene su espacio de datos completamente aislado (ver sección 6).

### Flujo de suscripción Stripe

- **Planes disponibles:** FREE, BASIC, PRO, ENTERPRISE — definidos en `travelhub/settings/base.py:523-533` (SAAS_PLAN_LIMITS).
- **Config en settings:** `base.py` — STRIPE_SECRET_KEY, STRIPE_PUBLISHABLE_KEY, STRIPE_WEBHOOK_SECRET, STRIPE_PRICE_IDS por plan (líneas 347-353).
- **Webhook Stripe:** `POST /finance/webhooks/stripe/` → `StripeWebhookView` en `apps/finance/views/views_webhooks.py`.
  - Validación obligatoria con `stripe.Webhook.construct_event()`. Fail-closed: 503 si secret falta, 401 si firma inválida.
  - Sin bypass DEBUG (eliminado en v1.1.0, protegido por test `test_bypass_debug_no_esta_en_views_webhooks`).
  - Idempotencia vía `select_for_update()` en `TransaccionPago.webhook_transaction_id`.
  - Eventos manejados: `checkout.session.completed`, `customer.subscription.deleted`, `invoice.payment_succeeded`, `invoice.payment_failed`.
- **Billing handlers** en `core/views/billing_*` cargados vía `import_string` desde `apps/finance/urls.py`.
- **Plan change / preview:** `core/views/billing_plan_change_views.py`.
- **Quota enforcement:** `SaaSLimitMiddleware` (`core/middleware_saas.py`) intercepta POST/PUT/PATCH, retorna HTTP 403 si `SaaSQuotaService.check_quota()` falla.
- **Plan almacenado en:** `AgenciaConfiguracion.plan` (CharField choices en `core/models/agencia.py`).
- **Límites por plan (base.py:523-533):**

```python
SAAS_PLAN_LIMITS = {
    "FREE":       {"users": 1,   "storage_mb": 100,   "leads_per_month": 20,    "sales_per_month": 20},
    "BASIC":      {"users": 2,   "storage_mb": 500,   "leads_per_month": 50,    "sales_per_month": 50},
    "PRO":        {"users": 10,  "storage_mb": 5000,   "leads_per_month": 500,   "sales_per_month": 500},
    "ENTERPRISE": {"users": 999, "storage_mb": 99999,  "leads_per_month": 99999, "sales_per_month": 99999},
}
```

### Binance Pay (estado: webhook real en views_webhooks.py; draft eliminado de payment_views.py)

- `BinanceWebhookView` draft (referencias a métodos inexistentes) eliminado de `apps/finance/views/payment_views.py` (v1.1.0, commit 05ee7b8).
- `POST /finance/webhooks/binance/` → `BinanceWebhookView` en `apps/finance/views/views_webhooks.py` con verificación HMAC-SHA256.
- Fail-closed: 503 si `BINANCE_WEBHOOK_SECRET` falta, 401 si firma inválida. Sin bypass DEBUG.
- Tests: 6 casos en `tests/test_webhooks_hardening.py` (`TestBinanceWebhookFailClosed`).

---

## 2. GLOSARIO DE DOMINIO

| Término | Definición |
|---|---|
| **Fee de agencia** | Comisión que cobra la agencia sobre el precio del proveedor. Campo `fee_agencia_interno` en `ItemVenta` (`apps/bookings/models/venta.py`). |
| **Boleto de tercero / BoletoImportado** | Boleto aéreo emitido por un GDS/consolidador e importado al sistema (PDF o TXT). Modelo `BoletoImportado` en `apps/bookings/models/venta.py`. |
| **Diferencial cambiario** | Ganancia/pérdida por diferencia entre tasa BCV oficial y tasa del mercado paralelo (VES). Se refleja en `PagoVenta.monto_igtf` y totales de `Factura` en doble moneda (USD/VES). |
| **IGTF** | Impuesto a los Grandes Transacciones Financieras (3% Venezuela). Se calcula automáticamente en `PagoVenta` cuando `aplica_igtf=True`. |
| **GDS** | Global Distribution System (Sabre, Amadeus, KIU, Copa SPRK). Sistemas de reserva aérea. |
| **PNR** | Passenger Name Record — Código alfanumérico de 6 caracteres de reserva en un GDS (ej: ABC123). |
| **IVA (VEN-NIF)** | IVA venezolano (16% general, 25% suntuario/turismo). Tasa default en `AgenciaConfiguracion.iva_por_defecto`. |
| **VEN-NIF** | Régimen fiscal venezolano de facturación electrónica (libro de ventas, IVA, ISLR). |
| **Retención ISLR** | Retención de Impuesto Sobre La Renta (5% sobre comisiones). Modelo `RetencionISLR` en `apps/finance/models_stubs.py`. |
| **Consolidador** | Mayorista que consolida boletos de múltiples aerolíneas y emite factura única a la agencia. |
| **Conciliación / SLOT** | Proceso de matching entre boleto emitido y asiento contable/consolidador. Modelo `ConciliacionBoleto`. |
| **LC (Línea de Crédito)** | Crédito que el consolidador otorga a la agencia. [VERIFICAR — modelo LineaCreditoProveedor asumido, no leído directamente]. |
| **FOID** | Form of Identification — campo que contiene documento de identidad del pasajero en boletos GDS (ej: IDPP123456). |
| **Tarifario** | Catálogo de precios de hoteles o paquetes. Modelo `HotelTarifario` (apps/bookings/). |
| **IATA Office ID** | Código alfanumérico de 8-9 caracteres que identifica la oficina emisora de un boleto (ej: BLA005RSJ, CCS00ESKA). |
| **BCV** | Banco Central de Venezuela — fuente oficial de la tasa de cambio USD/VES. Se sincroniza vía tarea Celery. |

---

## 3. STACK TECNOLÓGICO EXACTO

| Componente | Versión / Detalle | Verificado en |
|---|---|---|
| **Python** | 3.13 (target-version = "py313") | .ruff.toml |
| **Django** | 5.2.x (migración 0051+ aplicada) | core/migrations/ |
| **DRF** | djangorestframework | base.py INSTALLED_APPS |
| **Base de datos** | PostgreSQL 15-alpine | docker-compose.yml:39 |
| **PgBouncer** | Contenedor pgbouncer (opcional) | docker-compose.yml:71 |
| **Redis** | Instancia única con DBs separados (0=celery, 0=cache, 1=sessions) | docker-compose.yml:96, base.py:654-688 |
| **Frontend** | HTMX + Alpine.js + Tailwind CSS + Unfold Admin | base.py:121-157 + settings_unfold.py |
| **Celery** | django_celery_results + django_celery_beat, 2 colas: `celery` + `notifications` | celery.py:22-29 |
| **Stripe** | Python stripe library | base.py:347-353 |
| **Evolution API** (WhatsApp) | Servicio externo http://evolution:8080, container travelhub_evolution | docker-compose.yml:373 |
| **Gemini** (AI core) | google-genai; **gemini-2.5-flash** (default+vision+fallback), gemini-1.5-pro (razonamiento) | ai_engine.py:70-74 |
| **Sentry** | sentry-sdk con integraciones Django+Celery+Redis | production.py |
| **drf-spectacular** | OpenAPI 3.0 / Swagger / ReDoc, API v2.0.0 | base.py:433-517 |
| **Cloudflare R2** | Almacenamiento S3-compatible para archivos | base.py:303-327 |
| **django-axes** | Protección fuerza bruta (5 intentos, 1h cooloff, por username+IP) | base.py:725-732 |
| **Fernet (cryptography)** | Cifrado simétrico en reposo (ENCRYPTION_KEY) | core/fields.py |
| **WeasyPrint** | Generación de PDFs de boletos (síncrono) | parsers/pdf_generation.py |
| **Gotenberg** | Generación de PDFs vía container (alternativa) | .env.example:126 |
| **Whitenoise** | Servir estáticos en producción | base.py:166 |
| **django-cors-headers** | CORS management | base.py:168 |
| **Waffle** | Feature flags | base.py:140 |
| **Resend** | Email SMTP (producción) | base.py:539-554 |
| **Amadeus SDK** | Parser PNR + service | apps/automation/services/amadeus_service.py |
| **django-prometheus** | Métricas Prometheus en /prometheus/ | urls.py:135 |
| **PWA manual** | manifest.json + service-worker.js con rutas conectadas | urls.py:144-146, core/views/pwa_views.py |
| **SSO (OIDC/SAML)** | Implementación custom — sin librería externa verificada | core/sso/models.py, core/sso/views.py |
| **GitHub Actions CI** | .github/workflows/ci.yml (gitleaks, mypy, bandit, pip-audit) | CHANGELOG.md v1.1.0 |
| **Traefik** | v3.0 — reverse proxy + SSL (Let's Encrypt + Cloudflare DNS) | docker-compose.yml:6 |
| **Jaeger** | Distributed tracing (contenedor travelhub_jaeger) | docker-compose.yml:231 |

### Variables de entorno obligatorias

Definidas en `.env.example` (137 líneas). **Nunca** commitear `.env` ni `.env.local`.

| Variable | Propósito |
|---|---|
| SECRET_KEY | Clave secreta Django (session signing, CSRF) |
| DATABASE_URL | Connection string PostgreSQL |
| ENCRYPTION_KEY | Clave Fernet en base64 (32+ chars) para EncryptedCharField |
| ENCRYPTION_SALT | Salt adicional opcional para cifrado |
| CELERY_BROKER_URL | Redis para tareas Celery asíncronas |
| REDIS_URL | Redis para cache de Django |
| GEMINI_API_KEY | API key global de Google Gemini (puede sobreescribirse por agencia) |
| STRIPE_SECRET_KEY | Stripe API key (modo live en prod) |
| STRIPE_PUBLISHABLE_KEY | Stripe clave pública para frontend |
| STRIPE_WEBHOOK_SECRET | Verificación de firma Stripe — OBLIGATORIA, fail-closed |
| BINANCE_WEBHOOK_SECRET | Verificación HMAC-SHA256 Binance — OBLIGATORIA, fail-closed |
| TELEGRAM_BOT_TOKEN | Bot de Telegram para notificaciones |
| TELEGRAM_WEBHOOK_SECRET | Verificación timing-safe Telegram — OBLIGATORIA, fail-closed |
| WHATSAPP_MICROSERVICE_URL | URL de Evolution API (WhatsApp) |
| WHATSAPP_MICROSERVICE_TOKEN | Token de autenticación Evolution API |
| SENTRY_DSN | Error tracking (opcional en dev) |
| JWT_SIGNING_KEY | Clave independiente para JWT (default: SECRET_KEY si no se define) |
| USE_PGBOUNCER | Boolean — si True, CONN_MAX_AGE=0 para evitar fuga RLS |
| USE_R2 | Boolean — si True, usa Cloudflare R2 para media |
| R2_ACCESS_KEY_ID | Credenciales Cloudflare R2 |
| R2_SECRET_ACCESS_KEY | Credenciales Cloudflare R2 |
| R2_BUCKET_NAME | Nombre del bucket R2 |
| R2_ENDPOINT_URL | URL del endpoint R2 |
| RESEND_API_KEY | Email transaccional vía Resend SMTP |
| GOTENBERG_URL | URL del servicio Gotenberg para PDFs HTML→PDF |
| DJANGO_BASE_URL | URL interna Django para monitor proactivo WhatsApp |
| MONITOR_SERVICE_TOKEN | Token opcional para requests del monitor worker |

---

## 4. INFRAESTRUCTURA Y DEPLOY

### Docker Compose — 12 servicios (verificado en docker-compose.yml:463 líneas)

| Contenedor | Servicio | Imagen |
|---|---|---|
| travelhub_proxy | Traefik reverse proxy + SSL | traefik:v3.0 |
| travelhub_db | PostgreSQL primario | postgres:15-alpine |
| travelhub_pooler | PgBouncer (connection pooler) | [VERIFICAR — imagen exacta no leída] |
| travelhub_broker | Redis (broker Celery + cache + sessions) | [VERIFICAR — imagen exacta no leída] |
| travelhub_web | Django / Gunicorn (app principal) | Dockerfile custom |
| travelhub_nginx | Nginx static server | [VERIFICAR] |
| travelhub_jaeger | Jaeger distributed tracing | [VERIFICAR] |
| travelhub_worker | Celery worker (cola `celery`) | Mismo Dockerfile |
| travelhub_notifications | Celery worker (cola `notifications`) | Mismo Dockerfile |
| travelhub_beat | Celery Beat (scheduler) | Mismo Dockerfile |
| travelhub_evolution | Evolution API v2 (WhatsApp) | [VERIFICAR] |
| travelhub_evolution_db | PostgreSQL para Evolution | [VERIFICAR] |

**Redes Docker:** `travelhub_public` (proxy), `travelhub_private` (servicios internos).

**Volúmenes:** postgres_data, redis_data, static_volume, media_volume, evolution_data, evolution_db_data.

**Producción:** Dominio `travelhub.cc`, Traefik + Let's Encrypt + Cloudflare DNS, Cloudflare R2 para assets estáticos y media.

**CI/CD:** GitHub Actions — `.github/workflows/ci.yml` (10169 bytes):
- Job `secret-scan`: gitleaks-action@v2 con fetch-depth: 0 (historial completo).
- Job `lint`: ruff + mypy --ignore-missing-imports (con django-stubs).
- Job `security-scan`: bandit -r apps/ core/ + pip-audit (sin `|| true` — falla el build).
- Coverage threshold: --cov-fail-under=75.

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

**Settings auto-routing:** `travelhub/settings/__init__.py` lee DJANGO_ENV → carga development.py, production.py o testing.py. Default: development.

**Celery settings default:** `travelhub/celery.py:11` — `DJANGO_SETTINGS_MODULE` = `travelhub.settings.development` (corregido de `production`, fix P2-004).

---

## 5. MAPA DE ARCHIVOS CRÍTICOS

```
travelhub/                              # Paquete de configuración Django
├── settings/
│   ├── __init__.py                     # Auto-router: DJANGO_ENV → archivo de settings
│   ├── base.py                         # 783 líneas — config base compartida
│   ├── development.py                  # DEBUG=True, email console, AXES_ENABLED override
│   ├── production.py                   # HSTS, Sentry, SECURE_PROXY_SSL_HEADER
│   └── testing.py                      # Celery EAGER, cache local, sin R2
├── settings.py                         # Shim de compatibilidad (1226 bytes)
├── urls.py                             # 173 líneas — enrutador maestro
├── urls_api.py                         # 48 líneas — router DRF fusionado
├── celery.py                           # 117 líneas — App Celery, 2 colas
├── celery_beat_schedule.py             # 116 líneas — 19 tareas programadas
└── settings_unfold.py                  # 14158 bytes — tema visual Unfold Admin

core/                                   # App central — multi-tenancy, seguridad, modelos base
├── middleware.py                       # 538 líneas — ThreadLocalContextMiddleware (RLS)
│                                       #   MultiTenantDomainMiddleware (subdominios)
│                                       #   SecurityHeadersMiddleware (CSP+nonce)
│                                       #   system_context(), agency_context()
│                                       #   csp_report_view()
├── middleware_saas.py                  # SaaSLimitMiddleware — bloqueo por cuotas SaaS
├── middleware_onboarding.py            # OnboardingRedirectMiddleware
├── middleware_ai_ratelimit.py          # AIRateLimitMiddleware — throttle de IA
├── middleware_performance.py           # QueryCountDebugMiddleware, CacheHeaderMiddleware
├── middleware_plan_limits.py           # [VERIFICAR — coexiste con middleware_saas.py]
├── security.py                         # 230 líneas — get_agencia_or_403,
│                                       #   get_object_tenant_or_404,
│                                       #   filter_queryset_by_tenant,
│                                       #   get_user_active_agency (cache Redis TTL=30s)
│                                       #   agency_role_required(), invalidate_all_agency_caches()
├── fields.py                           # 137 líneas — EncryptedCharField, EncryptedTextField (Fernet)
├── validators.py                       # 209 líneas — antivirus_hook (ClamAV), sanitize_html (bleach),
│                                       #   validate_file_extension (magic bytes), PLAN_SIZE_LIMITS_MB
├── permissions.py                      # IsStaffOrGroupWrite, rol_requerido()
├── throttling.py                       # 77 líneas — AgenciaAIParserThrottle (20/min por agencia)
│                                       #   AIParserDailyQuotaThrottle (200/día)
│                                       #   DashboardRateThrottle, LiquidacionRateThrottle, etc.
├── signals.py                          # 243 líneas — Señal única consolidada BoletoImportado (P1-001)
├── signals_audit.py                    # 432 líneas — Auditoría con hash chain (Venta, Boleto, etc.)
├── signals_bypass.py                   # disable_signals() context manager con stack trace
├── api_registry.py                     # 20469 bytes — registro central de API
├── api/
│   ├── mixins/tenant.py                # TenantViewSetMixin (DRF) — filtro por agencia
│   ├── mixins/saas_mixin.py            # SaaSMixin (CBV Django + RBAC)
│   └── public_auth.py                  # APIKeyAuthentication, HasAPIKeyScope
├── models/
│   ├── base.py                         # 281 líneas — AgenciaMixin, AgenciaManager,
│   │                                   #   SoftDeleteModel, GlobalAwareAgenciaManager,
│   │                                   #   SaasQuerySet (bulk_create/update con agencia)
│   ├── agencia.py                      # 576 líneas — Agencia, AgenciaBranding,
│   │                                   #   AgenciaConfiguracion, UsuarioAgencia
│   ├── cron_api_key.py                 # 125 líneas — PBKDF2-HMAC-SHA256 (600K iter)
│   │                                   #   + lookup_hash SHA-256 para O(1) lookup
│   ├── api_keys.py                     # DEPRECATED — tabla eliminada (migración 0049)
│   │                                   #   Modelo Python sin backing table
│   ├── audit.py                        # AuditLog con hash chain
│   ├── ai.py                           # AIUsageLog — log de cada llamada a Gemini
│   ├── aeropuerto.py                   # Aeropuerto (catálogo global)
│   ├── ai_schemas.py                   # Pydantic schemas IA (23204 bytes)
│   ├── feature_flags.py                # FeatureFlag (Waffle)
│   ├── magic_link.py                   # MagicLinkToken
│   ├── historial_boletos.py            # AnulacionBoleto, HistorialCambioBoleto
│   ├── webhooks.py                     # Modelos de webhook
│   ├── numbering.py                    # Numeración automática de documentos
│   └── migration_checks.py            # Validaciones pre-migración
├── sso/
│   ├── models.py                       # SSOProvider — Azure AD, Okta OIDC/SAML,
│   │                                   #   Google Workspace, Generic OIDC/SAML
│   └── views.py                        # sso_login, sso_callback (12215 bytes)
├── views/
│   ├── cron_views.py                   # Endpoints cron (BCV sync, reminders, cierre)
│   ├── auth_views.py                   # MagicLinkRequestView, MagicLinkVerifyView, TokenLogoutView
│   ├── pwa_views.py                    # manifest(), service_worker(), offline()
│   ├── status_views.py                 # status_page, status_api (solo staff)
│   ├── marketing_views.py              # public_landing, public_pricing, parse_demo, lead_magnet
│   ├── docs_views.py                   # docs_index, docs_page, public_manual
│   ├── health_views.py                 # health_check
│   ├── dev_portal_views.py             # developer_portal
│   ├── onboarding_views.py             # SaaSOnboardingView, OnboardingAgencyView
│   └── auditoria_views.py              # api_audit_logs
├── management/commands/
│   ├── rotate_encryption_key.py        # Rotación de ENCRYPTION_KEY en batches
│   ├── generate_cron_key.py            # Generar CronApiKey desde CLI
│   └── setup_production.py             # Setup inicial de producción
├── services/                           # Servicios de negocio core
└── chatbot/                            # Chatbot IA

apps/
├── automation/                         # Core de IA — parser, agente, copywriter
│   ├── services/
│   │   ├── ai_engine.py                # 632 líneas — AIEngine (clase central Gemini)
│   │   │                               #   DEFAULT_MODEL="gemini-2.5-flash"
│   │   │                               #   PRO_MODEL="gemini-1.5-pro"
│   │   │                               #   VISION_MODEL="gemini-2.5-flash"
│   │   │                               #   FALLBACK_MODEL="gemini-2.5-flash"
│   │   ├── ai_agent.py                 # TravelHubAgent — 19 herramientas Gemini function calling
│   │   ├── ai_copywriter.py            # AICopywriter — captions Instagram para hoteles
│   │   ├── ticket_parser_service.py    # Orquestador principal de parseo
│   │   ├── ai_tools.py                 # 891 líneas — AgentTools (19 funciones del agente)
│   │   ├── ai_router.py                # Router de IA — decide qué modelo usar
│   │   ├── venta_automation.py         # VentaAutomationService
│   │   ├── amadeus_service.py          # Parser PNR Amadeus
│   │   ├── linkeo_service.py           # Servicio de linkeo de boletos
│   │   └── hotel_parser_service.py     # Parser de tarifarios de hoteles
│   └── parsers/
│       ├── ai_universal_parser.py      # 356 líneas — UniversalAIParser (GOD MODE 2.0)
│       │                               #   SYSTEM_PROMPT 13 reglas estrictas
│       │                               #   Sabre, Amadeus, KIU, Copa SPRK,
│       │                               #   Estelar Web, Rutaca Web, Avior, Wingo
│       ├── gemini_parser.py            # 8747 bytes — GeminiParser (BaseTicketParser)
│       ├── kiu_parser.py               # 28706 bytes — parser regex KIU
│       ├── base_parser.py              # 29853 bytes — BaseTicketParser, ParsedTicketData
│       ├── ticket_parser.py            # 17407 bytes — extract_data_from_text (entrada pública)
│       ├── extraction.py               # 10690 bytes — ExtractionService
│       ├── normalization.py            # 17277 bytes — DataNormalizationService
│       ├── pdf_generation.py           # 10955 bytes — PdfGenerationService
│       ├── persistence.py              # 5319 bytes — BoletoPersistenceService
│       ├── registry.py                 # Registro de parsers disponibles
│       ├── console_parser.py           # 7530 bytes — parser de consola GDS
│       ├── parsing_utils.py            # 9381 bytes — utilidades de parseo
│       ├── airline_utils.py            # 8721 bytes — utilidades de aerolíneas
│       ├── adapter.py                  # Adaptador de parsers
│       ├── venta_builder.py            # 7332 bytes — constructor de Ventas desde parseo
│       ├── tarifario_parser.py         # 9385 bytes — parser de tarifarios
│       ├── supplier_report_parser.py   # Parser de reportes de proveedores
│       ├── text_extraction.py          # Extracción de texto de PDFs
│       ├── receipt_parsers/            # Parsers de recibos web específicos
│       └── legacy/                     # Parsers legacy
├── bookings/
│   ├── models/
│   │   ├── venta.py                    # Venta, ItemVenta, BoletoImportado,
│   │   │                               #   FeeVenta, PagoVenta, VentaAuditFinding
│   │   ├── servicios.py                # ProductoServicio (TipoProductoChoices)
│   │   └── proveedores.py              # Proveedor
│   └── urls.py                         # 299 líneas
├── finance/
│   ├── models.py                       # Factura (AgenciaMixin), ItemFactura, Pago, FiscalConfig
│   ├── models_stubs.py                 # 682 líneas — stubs legacy (managed=False):
│   │                                   #   FacturaConsolidada, RetencionISLR,
│   │                                   #   TaxRefundOpportunity, LinkDePago,
│   │                                   #   ConciliacionBoleto, GastoOperativo
│   ├── models_pg.py                    # Modelos con raw SQL / PG views
│   ├── services/
│   │   ├── facturacion_service.py      # FacturacionService.generar_factura_desde_venta()
│   │   └── factura_service.py          # FacturaService
│   └── urls.py                         # 232 líneas — router finanzas + webhooks
├── crm/                                # Clientes, pasajeros, WhatsApp
├── contabilidad/
│   └── models.py                       # CuentaContable, AsientoContable,
│                                       #   MovimientoContable, PlanContable, DetalleAsiento
├── communications/
│   └── services/evolution_api_service.py  # Evolution API (WhatsApp)
├── cotizaciones/                       # Cotizaciones + AI Magic-GPT
├── marketing/                          # Automatización de marketing
├── cms/                                # Content Management
└── common/
    ├── services/
    │   ├── saas_quota_service.py       # SaaSQuotaService.check_quota()
    │   ├── bi_service.py               # Business Intelligence KPIs
    │   ├── catalog_service.py          # CatalogNormalizationService (airports_master.json)
    │   └── circuit_breaker.py          # Circuit Breaker para tareas Celery
    └── models.py                       # Pais, Ciudad, Aerolinea, Moneda, UserProgress
```

---

## 6. LÓGICA DE MULTI-TENANCY (4 CAPAS DE DEFENSA)

### Capa 1: AgenciaManager.get_queryset() — core/models/base.py:61

Manager por defecto de todos los modelos que heredan `AgenciaMixin`. Aplica 3 filtros en orden:

1. **Soft delete:** si el modelo hereda `SoftDeleteModel`, filtra `is_deleted=False` (línea 70-71).
2. **System context bypass:** si `is_system_context()` retorna True, retorna el queryset sin filtro (línea 74-75).
3. **Multi-tenancy** según `agency_var` (ContextVar del middleware):
   - **Caso A** (agencia activa): `queryset.filter(agencia=agencia)` — solo registros de esa agencia (línea 85).
   - **Caso B** (superuser sin agencia): devuelve todo — God Mode global (línea 88-89).
   - **Caso C** (pytest / manage.py): sin filtro — detectado vía constantes de módulo `_IS_PYTEST`, `_IS_MANAGEMENT_COMMAND` (líneas 11-16, evaluadas UNA VEZ al importar — fix P2-006).
   - **Caso D** (usuario normal sin agencia): `queryset.none()` — falla cerrada (línea 97).

```python
# core/models/base.py:9-16 — Constantes evaluadas UNA VEZ al importar
_IS_PYTEST = "pytest" in sys.modules
_IS_MANAGEMENT_COMMAND = bool(
    sys.argv and sys.argv[0].endswith("manage.py")
    and any(arg in sys.argv for arg in ["makemigrations", "migrate", "shell", "check", "test"])
)
```

**SaasQuerySet** (línea 19-43): Sobreescribe `update()` y `bulk_create()` para inyectar agencia automáticamente en operaciones bulk — no se puede bypassear el tenant con queryset masivos.

### Capa 2: TenantViewSetMixin — core/api/mixins/tenant.py

Para DRF ViewSets. Sobreescribe `get_queryset()` (filtrado por agencia) y `perform_create()` (asigna agencia). Superusuarios hacen bypass.

### Capa 3: SaaSMixin — core/api/mixins/saas_mixin.py (378 líneas)

Para Django Class-Based Views. Similar a TenantViewSetMixin + verificación de roles RBAC (admin, gerente, vendedor, contador, consulta).

### Capa 4: Helpers de seguridad — core/security.py

- `get_agencia_or_403(request)` — extrae agencia del request, 403 si no tiene (línea 183-188).
- `get_object_tenant_or_404(model, agencia, **kwargs)` — get_object_or_404 con filtro de agencia (línea 191-212).
- `filter_queryset_by_tenant(queryset, agencia)` — filtra queryset por agencia (línea 215-229).
- `get_user_active_agency(user)` — obtiene agencia activa con cache Redis (TTL=**30s**, fix P1-004, línea 43).
- `agency_role_required(allowed_roles)` — decorador de vistas para RBAC (línea 122-158).
- `invalidate_user_agencia_cache(user_id)` — invalida cache individual (línea 95-98).
- `invalidate_all_agency_caches(agencia_id)` — invalida cache para todos los usuarios de la agencia (línea 101-109).

### Middleware RLS en PostgreSQL

`ThreadLocalContextMiddleware` (`core/middleware.py:137`) al inicio de cada request:

```sql
SET LOCAL app.current_agencia_id = '<uuid>';
SET LOCAL app.bypass_rls = 'true'|'false';
-- Al final: purgadas automáticamente al commit/rollback (ATOMIC_REQUESTS=True)
```

**Bypass RLS** se activa SOLO cuando: el usuario es superuser, está en ruta /admin/, y NO está impersonando (líneas 296-304).

**Limpieza garantizada** (líneas 320-348): bloque `finally` resetea todas las ContextVars con token-based reset y limpia las variables RLS en la DB.

**Protección CONN_MAX_AGE:** `USE_PGBOUNCER` condicional en `base.py:221-224` — si True, `CONN_MAX_AGE=0` para evitar fuga RLS cross-tenant.

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

### AgenciaMixin.save() — validación en escritura (base.py:231-265)

1. Si no tiene `agencia_id`, intenta asignar del contexto actual.
2. Si usuario es superuser sin system_context, lanza `PermissionDenied` ("God Mode: selecciona agencia primero").
3. **Validación cruzada:** si `self.agencia_id != current_context_agency.id` y no es superuser → `PermissionDenied`.

### MultiTenantDomainMiddleware — core/middleware.py:498-538

Resuelve tenant por dominio o subdominio:
1. Si host es localhost/main domain → `request.agencia = None`.
2. Busca `Agencia.dominio_personalizado == host`.
3. Busca subdominio via `AgenciaConfiguracion.subdominio_slug`.
4. Si no encuentra → Http404.

### Modelos que heredan AgenciaMixin

Todos en apps/: Venta, ItemVenta, Factura, BoletoImportado, ProductoServicio, Cliente, CuentaContable, etc.

`SoftDeleteModel` añade: is_deleted, deleted_at, with_deleted manager, delete() (lógico), hard_delete() (físico), restore().

### Modelos GLOBALES (sin AgenciaMixin)

FeatureFlag, AuditLog, plantillas de notificación. Usan `GlobalAwareAgenciaManager` (base.py:100) que expone registros con `agencia__isnull=True` (plantillas globales) junto con los de la agencia activa.

---

## 7. ARQUITECTURA DE LA IA INTERNA

### 7.1 Motor Central — AIEngine (apps/automation/services/ai_engine.py)

```python
class AIEngine:                             # Línea 64
    DEFAULT_MODEL  = "gemini-2.5-flash"     # Parseo rápido y copywriting
    PRO_MODEL      = "gemini-1.5-pro"       # Razonamiento complejo
    VISION_MODEL   = "gemini-2.5-flash"     # Análisis de imágenes/PDFs
    FALLBACK_MODEL = "gemini-2.5-flash"     # Si el modelo principal falla
```

Resolución de API key (`get_gemini_api_key(agency=None)`, línea 39-61):
1. Busca en `AgenciaConfiguracion.gemini_api_key` (vía `configuracion_v2`, API key por agencia — enterprise).
2. Fallback: `os.environ["GEMINI_API_KEY"]` o `settings.GEMINI_API_KEY` (global).

Cliente Gemini (`_get_client()`, línea 82-112):
- Cache de clientes por API key (`_clients_cache`).
- Timeout HTTP: 30 segundos (`HttpOptions(timeout=30000)`).
- Lazy import de `google.genai` y `google.genai.types`.

Excepciones custom: `CircuitBreakerException`, `QuotaExhaustedException` (HTTP 429), `GeminiConfigurationError`.

Rate limiting: `AgenciaAIParserThrottle` — 20 req/min, 200 req/día por agencia (core/throttling.py:40-68).

Logging: `AIUsageLog` (core/models/ai.py) registra cada llamada (modelo, tokens, tiempo, costo estimado).

---

### 7.2 Ticket Parser Pro — Flujo completo

Orquestador: ticket_parser_service.py (apps/automation/services/).

Estrategia dual (AI-first + Regex fallback):

```
PDF/TXT input → ExtractionService.extract_text()
     |
     +--→ UniversalAIParser.parse()      ← PRIMERO (GOD MODE, Gemini 2.5-flash)
     |          | Falla / texto < 50 chars
     |          v
     +--→ GeminiParser / KiuParser / ConsoleParser / Regex parsers  ← FALLBACK
               |
               v
         DataNormalizationService.normalize_ticket_data()
               |
               v
         PdfGenerationService (WeasyPrint síncrono / Celery async si disponible)
               |
               v
         BoletoPersistenceService.save_to_db()
               |
               v
         BoletoImportado (DB) → estado_parseo: OK/ERR/PEN
```

UniversalAIParser (apps/automation/parsers/ai_universal_parser.py):
- SYSTEM_PROMPT de 13 reglas estrictas de extracción ("GOD MODE 2.0").
- Soporta: Sabre, Amadeus, KIU, Copa SPRK, Estelar Web, Rutaca Web, Avior, Wingo.
- Detecta prorrateo multi-pasajero y separa en boletos individuales.
- Truncado a 15,000 chars ahora logea warning + flag `_text_was_truncated` (fix P1-006).

GeminiParser (apps/automation/parsers/gemini_parser.py):
- 8747 bytes — prompt de 13+ reglas detalladas con ejemplos GDS.
- can_parse(text): retorna True si len(text) > 50.

KiuParser (apps/automation/parsers/kiu_parser.py):
- 28,706 bytes — parser regex especializado en boletos KIU/Avior/Rutaca.

Parsers adicionales verificados en directorio:
- `console_parser.py` (7530 bytes) — parser de pantallas de consola GDS.
- `tarifario_parser.py` (9385 bytes) — parser de tarifarios de hotel.
- `supplier_report_parser.py` (3405 bytes) — parser de reportes de proveedores.
- `venta_builder.py` (7332 bytes) — constructor de Ventas desde datos parseados.
- `receipt_parsers/` — subdirectorio con parsers de recibos web específicos.

---

### 7.3 TravelHub Agent — TravelHubAgent (apps/automation/services/ai_agent.py)

Agente ERP completo con Gemini Function Calling automático (max. 10 llamadas remotas por query).

19 herramientas disponibles (clase AgentTools en ai_tools.py, 891 líneas):
- get_sales_stats(days) — estadísticas de ventas por período
- get_financial_kpis() — KPIs rápidos P&L
- get_pending_payments() — pagos pendientes
- get_financial_report() — reporte financiero completo
- get_client_info() — info de clientes del CRM
- get_quote_status() — estado de cotizaciones
- get_recent_expenses() — gastos operativos
- generate_cms_content() — artículos de blog en Markdown
- list_cms_content() — listado de contenido CMS
- get_reconciliation_summary() — resumen de conciliación
- get_reconciliation_discrepancies() — discrepancias de conciliación
- get_cash_flow_summary() — flujo de caja actual
- get_cashflow_forecast() — proyección 30 días
- get_account_balance() — saldo de cuenta contable
- generate_marketing_copy() — copy de marketing para hoteles
- encode_iata_location(city) — ciudad → código IATA
- decode_iata_code(code) — código IATA → detalles aeropuerto
- find_nearest_airports(lat, lon) — aeropuertos cercanos a coordenadas
- get_travel_requirements(origin, dest) — visa, pasaporte, vacunas

Acceso a datos: Todas las herramientas usan `get_current_agency()` del middleware — datos 100% aislados por tenant.

Manejo de errores: try/except Exception devuelve string descriptivo al usuario sin exponer tracebacks.

---

### 7.4 AI Copywriter — AICopywriter (apps/automation/services/ai_copywriter.py)

- Genera captions de Instagram para hoteles del catálogo (HotelTarifario).
- Usa ai_engine.call_gemini(prompt) con tono: PROFESIONAL_AVENTURERO, FORMAL, AVENTURERO, ROMANTICO.
- Fallback: string de error descriptivo si ai_engine.is_ready es False.

---

## 8. CONTRATO DE API / ENDPOINTS PRINCIPALES

### Autenticación y acceso

| Método | Ruta | Propósito | Auth |
|---|---|---|---|
| POST | /api/auth/jwt/obtain/ | Obtener JWT (access + refresh) | Público |
| POST | /api/auth/jwt/logout/ | Invalidar refresh token | JWT |
| GET | /auth/magic-request/ | Solicitar magic link por email | Público |
| GET | /auth/magic/\<token\>/ | Verificar magic link → sesión | Público |
| GET | /sso/login/\<provider_id\>/ | Iniciar SSO (OIDC/SAML) | Público |
| GET | /sso/callback/\<provider_id\>/ | Callback SSO | Público |

### Sistema e infraestructura

| Método | Ruta | Propósito | Auth |
|---|---|---|---|
| GET | /health/ | Health check del sistema | Público |
| GET | /health/metrics/ | Métricas para monitoreo | Público |
| GET | /prometheus/ | Métricas Prometheus | Público |
| GET | /api/schema/ | OpenAPI schema JSON | Staff (prod) |
| GET | /api/docs/ | Swagger UI | Staff (prod) |
| GET | /api/redoc/ | ReDoc UI | Staff (prod) |
| GET | /csp-report/ | Receptor de violaciones CSP (rate limited: 5/min/IP) | Público |
| GET | /status/ | Status page del sistema | Staff |
| GET | /manifest.json | PWA manifest | Público |
| GET | /service-worker.js | PWA service worker | Público |
| GET | /developers/ | Portal para desarrolladores | Staff (prod) |

### Cron endpoints (protegidos con CronApiKey)

| Método | Ruta | Propósito | Auth |
|---|---|---|---|
| GET/POST | /system/api/cron/sincronizar-bcv/ | Sync tasa BCV | CronApiKey |
| GET/POST | /system/api/cron/recordatorios-pago/ | Recordatorios de pago | CronApiKey |
| GET/POST | /system/api/cron/cierre-mensual/ | Cierre contable mensual | CronApiKey |

### Bookings (Reservas)

| Método | Ruta | Propósito | Auth |
|---|---|---|---|
| GET/POST | /api/proveedores/ | CRUD proveedores | Session/Token |
| GET/POST | /api/productoservicio/ | CRUD productos/servicios | Session/Token |
| GET/POST | /api/ventas/ | CRUD ventas | Session/Token |
| GET | /api/boletos/buscar/ | Búsqueda de boletos importados | Session/Token |
| POST | /api/boletos/upload/ | Upload boleto (PDF/TXT) | Session/Token |
| POST | /api/boletos/\<id\>/reintentar-parseo/ | Reintentar parsing IA | Session/Token |
| POST | /api/boletos/\<id\>/crear-venta/ | Crear Venta desde boleto | Session/Token |

### Finance

| Método | Ruta | Propósito | Auth |
|---|---|---|---|
| GET/POST | /api/facturas/ | CRUD facturas | Session/Token |
| GET | /api/billing/plans/ | Listar planes SaaS + precios | Session/Token |
| POST | /api/billing/checkout/ | Crear sesión Stripe checkout | Session/Token |
| POST | /api/billing/portal/ | Stripe customer portal | Session/Token |
| POST | /api/billing/change-plan/ | Cambiar plan | Session/Token |
| POST | /api/billing/preview-change/ | Preview de cambio de plan | Session/Token |
| POST | /api/billing/downgrade-free/ | Downgrade a plan FREE | Session/Token |
| POST | /finance/webhooks/stripe/ | Webhook Stripe (sin CSRF) | Público (firma Stripe) |
| POST | /finance/webhooks/binance/ | Webhook Binance Pay | Público (HMAC-SHA256) |

### CRM y Comunicaciones

| Método | Ruta | Propósito | Auth |
|---|---|---|---|
| GET/POST | /api/clientes/ | CRUD clientes | Session/Token |
| GET/POST | /api/pasajeros/ | CRUD pasajeros | Session/Token |
| POST | /crm/webhook/whatsapp/ | Webhook WhatsApp entrante | Público (firma) |
| POST | /crm/webhook/evolution/ | Webhook Evolution API | Público (firma) |
| POST | /api/push/subscribe/ | Suscribir a push notifications | Session/Token |
| POST | /api/push/unsubscribe/ | Desuscribirse de push | Session/Token |
| POST | /i18n/set_language/ | Cambiar idioma de sesión | Session |
| GET/POST | /api/audit-logs/ | Logs de auditoría | Session/Token (staff) |
| POST | /api/parse-demo/ | Demo de parseo (landing page) | Público |
| GET | /api/lead-magnet/ | Descarga de lead magnet | Público |

### Tareas Celery Beat programadas (19 tareas — celery_beat_schedule.py)

| Tarea | Frecuencia | Propósito |
|---|---|---|
| process_incoming_emails | Cada 2 min | Procesar emails entrantes |
| check_passport_expiry | Diaria 9:00 | Verificar pasaportes por vencer |
| check_client_birthdays | Diaria 10:00 | Felicitaciones de cumpleaños |
| check_pending_payments | Diaria 11:00 | Recordatorios de pagos pendientes |
| sync_bcv_rates | L-V 9:00 y 13:00 | Sincronizar tasa BCV |
| backup_database_task | Diaria 3:00 | Backup de base de datos |
| monitorear_tiempos_limite | Cada 15 min | Monitorear límites de reservas |
| check_upcoming_flights | Diaria 17:00 | Vuelos del día siguiente |
| enviar_recordatorios_vuelo | Cada hora | Recordatorios de vuelo |
| limpiar_axes_logs | Mensual (día 1) | Limpiar logs de django-axes |
| limpiar_sesiones_expiradas | Diaria 3:00 | Purgar sesiones expiradas |
| limpiar_celery_results | Semanal (dom) | Purgar resultados de Celery |
| ejecutar_reconciliacion_contable | Diaria 1:00 | Reconciliación contable automática |
| ejecutar_cobranza_ia | Diaria 20:00 | Cobranza IA automatizada |
| fetch_all_qr_codes_task | Cada 60s | Renovar QR WhatsApp para todas las agencias |
| monitor_whatsapp_health | Cada 5 min | Monitor proactivo WhatsApp → alerta Telegram |
| process_scheduled_whatsapp_messages | Cada 60s | Enviar mensajes WhatsApp programados |
| retry_queued_boletos_task | Cada 10 min | Reintentar boletos en cola/tránsito (P3-001) |
| send_lead_followup_email | Cada hora | Follow-up de leads |

---

## 9. SEGURIDAD Y REGLAS DE ORO

### Medidas implementadas y verificadas

1. **Cifrado Fernet** (core/fields.py:24-137): EncryptedCharField/EncryptedTextField cifran en reposo con ENCRYPTION_KEY. Detecta doble cifrado (no recifra si empieza con `gAAAAA`, línea 63). `_decrypt()` reporta a Sentry vía `capture_exception()` y **retorna string vacío** — NO lanza ValueError (línea 71-87). `_encrypt()` lanza `ValueError` si falla (línea 69).

2. **CronApiKey con PBKDF2:** core/models/cron_api_key.py — `pbkdf2_hmac("sha256", 600_000 iteraciones)` (línea 10). `lookup_hash` (SHA-256) para O(1) lookup (línea 46-53). Backward-compat con keys legacy SHA256 vía `_verify_key()` (línea 21-27).
   ATENCIÓN: `APIKey` en `core/models/api_keys.py` es dead code — tabla eliminada (migración 0049). Modelo Python existe sin backing table. Marcado DEPRECATED.

3. **Anti-fuerza bruta (django-axes):** 5 intentos fallidos, 1h cooloff, por username+IP. `AXES_ENABLED=True` default (base.py:725-732). Handler: `AxesCacheHandler` usando Redis.

4. **Row-Level Security (RLS):** SET LOCAL app.current_agencia_id al inicio de cada request (middleware.py:306). `ATOMIC_REQUESTS=True` garantiza purga automática al final (base.py:241). Limpieza redundante en bloque `finally` del middleware (línea 340-348).

5. **CSP con nonces por request:** SecurityHeadersMiddleware (middleware.py:353-446) inyecta CSP con nonce. `strict-dynamic` en script-src. `unsafe-eval` presente en script-src globalmente (pendiente migración a @alpinejs/csp-bundle, línea 377). CSP personalizable por agencia vía `AgenciaConfiguracion.csp_directives` (líneas 411-428).

6. **Webhooks fail-closed (v1.1.0):**
   - Stripe: `stripe.Webhook.construct_event()` obligatorio. 503/401 si falla.
   - Binance: HMAC-SHA256 obligatorio. 503/401 si falla.
   - Telegram: `hmac.compare_digest` timing-safe. 403 si falta o inválido.
   - Test anti-regresión: `test_bypass_debug_no_esta_en_views_webhooks` verifica que la cadena "DEBUG" no esté en views_webhooks.py.

7. **Validación de archivos** (core/validators.py): Extensiones permitidas (línea 19), magic bytes validation (línea 79-106), ClamAV (try/except fallback, línea 118-144), sanitización de filename (línea 42-48), límites por plan (línea 34-39: FREE=2MB, BASIC=5MB, PRO=10MB, ENTERPRISE=25MB).

8. **Sanitización HTML:** `sanitize_html()` (línea 192-208) usa bleach con whitelist. Fallback seguro: `strip_tags()` si bleach no instalado.

9. **JWT signing key separada:** `JWT_SIGNING_KEY` (base.py:746, default SECRET_KEY). Separada para limitar impacto si SECRET_KEY se compromete. HS256, 30min access, 7 días refresh, rotación automática.

10. **God Mode timeout:** `system_context()` alerta si dura más de 60s (middleware.py:93-98). Impersonación de superusuarios tiene timeout de 30 minutos (middleware.py:201-211).

11. **Protección IDOR:** `get_object_tenant_or_404()` (security.py:191-212) debe usarse en toda vista funcional.

12. **SSO/SAML por agencia:** SSOProvider model en core/sso/models.py — cada agencia puede configurar Azure AD, Okta OIDC/SAML, Google Workspace o Generic OIDC/SAML. auto_provision=True crea usuario automáticamente si no existe.

13. **Auditoría con hash chain:** signals_audit.py (432 líneas) registra CREATE/UPDATE/DELETE en AuditLog para Venta, BoletoImportado y otros modelos críticos. Soporta bypass vía `are_signals_blocked()`.

14. **CSP report endpoint con rate limiting:** csp_report_view (middleware.py:449-495) — máximo 5 reportes/min/IP, payload máximo 10KB.

15. **Throttling por agencia:** 6 clases de throttle (core/throttling.py) — dashboard, liquidación, reportes, upload, AI parser quota (20/min), AI parser daily (200/día). Throttle se aplica por ID de agencia, no por IP.

### Reglas del Repositorio (NUNCA violar)

1. No inventar librerías. Toda librería debe estar en requirements/ e INSTALLED_APPS.
2. Validar en modelos. AgenciaMixin.save() valida cruce de datos (base.py:255-263).
3. No saltarse el filtro de agencia. No usar `.all_objects` en vistas de usuario sin justificación.
4. Usar `system_context()` con reason obligatoria. Logea stack trace. Alerta si dura > 60s.
5. No exponer secretos. ENCRYPTION_KEY, SECRET_KEY, JWT_SIGNING_KEY solo en .env.local.
6. Backward compatibility de hashes. `_verify_key()` soporta PBKDF2 y SHA256 legacy.
7. No romper `ATOMIC_REQUESTS`. Endpoints públicos (health): `@transaction.non_atomic_requests`.
8. Nunca añadir bypass `if DEBUG` a verificación de webhooks. Test anti-regresión en CI.
9. No exponer `str(e)` en respuestas 500. Usar `error_id` + `logger.exception()`.
10. Django ORM estricto — NO usar SQL directo para manipular entidades de negocio (regla AGENTS.md).
11. Detección de ciudades Sabre — expresiones regulares deben usar `[\t ]` en vez de `\s` (regla AGENTS.md).
12. Inicialización de catálogo — `CatalogNormalizationService._airports_master` debe validar `if not cls._airports_master:` para permitir reintentos (regla AGENTS.md).

---

## 10. BUGS Y LIMITACIONES CONOCIDAS (deuda técnica, no en trabajo activo)

### Modelos stub / dead code conocidos

| Modelo | Estado | Ubicación |
|---|---|---|
| FacturaFiscal | managed=False, tabla no existe en prod | apps/finance/models_stubs.py |
| APIKey | DEPRECATED, tabla eliminada (migración 0049) | core/models/api_keys.py |
| FacturaConsolidada | Stub legacy solo para tests | apps/finance/models_stubs.py |

### Deuda técnica residual (completamente resueltas — REMEDIATION_PLAN.md)

| ID | Descripción | Estado |
|---|---|---|
| P1-002 | celery.py importa `settings` a nivel de módulo | ✅ RESUELTO — import diferido con try/except |
| P1-005 | `locale.setlocale` monkey patch doble | ✅ RESUELTO — eliminado de travelhub/__init__.py, consolidado en core/apps.py con guard _is_safe_patch |
| P2-006 | AgenciaManager parsea sys.argv | ✅ RESUELTO — constantes de módulo _IS_PYTEST y _IS_MANAGEMENT_COMMAND usadas universalmente |
| P2-005 | Mapa de meses GDS duplicado | ✅ RESUELTO — centralizado en apps.automation.parsers.normalization (GDS_MONTH_EN, GDS_NUM_TO_EN, GDS_SHORT_TO_NUM) |

### Integraciones incompletas

| Item | Estado |
|---|---|
| PWA cache offline (service worker) | ✅ RESUELTO — Service Worker v4 con Cache-First para static/media y Network-First/Stale-While-Revalidate |
| i18n español | ✅ RESUELTO — 325 cadenas traducidas y compiladas (.po / .mo) |
| CSP unsafe-eval en admin (Alpine.js) | Pendiente migración @alpinejs/csp-bundle, middleware.py:377 |
| SSO sso_callback flow completo | Modelo y views existen pero flow end-to-end no auditado |

---

## 11. BRECHAS EN REPARACIÓN (trabajo activo — rama hardening/operational-risks)

### ✅ Resueltas (verificado en REMEDIATION_PLAN.md, auditoría 2026-07-21)

| ID | Brecha | Fix verificado |
|---|---|---|
| P0-002 | IDOR BoletoRetryParseAPIView | ✅ `get_object_tenant_or_404()` en boleto_views.py:167 |
| P0-003 | IDOR VentaDoubleInvoiceAPIView | ✅ `get_object_tenant_or_404(Venta, agencia)` en boleto_views.py:365 |
| P0-006 | Traceback expuesto en respuesta 500 | ✅ `error_id` + `logger.exception()`, sin `str(e)` |
| P1-001 | Doble signal post_save BoletoImportado | ✅ Señal única consolidada (signals.py:33-59, comentario P1-001) |
| P1-002 | celery.py import temprano de settings | ✅ Import de settings diferido y protegido con try/except |
| P1-003 | PgBouncer + CONN_MAX_AGE fuga RLS | ✅ `USE_PGBOUNCER` condicional en base.py:221-224 |
| P1-004 | Cache agencia TTL=120s | ✅ Reducido a 30s + `invalidate_all_agency_caches()` (security.py:43) |
| P1-005 | Doble implementación locale patch | ✅ Removido de travelhub/__init__.py, resuelto vía `core/apps.py` |
| P1-006 | UniversalAIParser truncado silencioso | ✅ `logger.warning` + flag `_text_was_truncated` |
| P1-007 | `_send_factura_whatsapp` `.apply()` síncrono | ✅ Usa `.delay()` con try/except (signals.py:239-242) |
| P2-002 | Archivos debug en raíz con credenciales | ✅ No hay archivos debug_* ni temp_* en raíz |
| P2-004 | celery.py default `settings.production` | ✅ Default cambiado a `travelhub.settings.development` (celery.py:11) |
| P2-005 | Mapa de meses GDS duplicado | ✅ Centralizado en `apps.automation.parsers.normalization` |
| P2-006 | sys.argv inline residuales | ✅ Reemplazados por `_IS_MANAGEMENT_COMMAND` constante de módulo |
| — | Antivirus hook sin fallback | ✅ `antivirus_hook()` usa try/except, logea warning si ClamAV no disponible |
| — | Bleach fallback inseguro | ✅ `sanitize_html()` usa `strip_tags()` como fallback seguro |
| — | Decryption failure silencioso | ✅ `_decrypt()` reporta a Sentry y retorna cadena vacía |
| — | API keys con SHA256 raw | ✅ Migrado a PBKDF2-HMAC-SHA256 (600K iter + salt) + lookup_hash O(1) |
| — | Signal bypass sin auditoría | ✅ `disable_signals()` logea stack trace del caller |
| — | Axes deshabilitado en dev | ✅ `AXES_ENABLED=True` default |
| — | JWT compartiendo SECRET_KEY | ✅ `JWT_SIGNING_KEY` variable independiente |
| — | Bandit deshabilitado en scripts | ✅ Eliminado "S" de per-file-ignores en .ruff.toml |
| — | Encryption key rotation | ✅ Nuevo comando `rotate_encryption_key` que re-cifra en batches |
| — | Stripe flow incompleto | ✅ StripeWebhookView documentado — eventos, idempotencia, firma |
| — | Binance dead code | ✅ BinanceWebhookView draft eliminado |
| — | Webhook DEBUG bypass | ✅ Sin `if DEBUG` en ningún webhook (test anti-regresión en CI) |
| — | CI/CD pipeline ausente | ✅ GitHub Actions con gitleaks, mypy, bandit, pip-audit |
| — | Pre-commit hooks | ✅ detect-private-key, check-merge-conflict, check-added-large-files |
| — | system_context() sin timeout | ✅ max_seconds=60, stack trace del caller en audit logger |
| — | mypy sin adoption plan | ✅ 5 módulos con strict=True pasando sin errores |

### ❌ Pendiente

| Brecha | Prioridad | Notas |
|---|---|---|
| alpinejs/csp-bundle | P3 | Eliminar unsafe-eval de CSP (actualmente global en script-src) |
| SSO end-to-end audit | P3 | Auditar flow completo de sso_callback |


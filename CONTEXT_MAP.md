# CONTEXT_MAP.md — Mapa Cerebral de TravelHub

> **Ultima verificacion contra codigo real:** 2026-07-26
> **Rama/commit revisado:** `hardening/operational-risks` @ `d35a1bfc`
> **Verificado por:** IA (Antigravity) — lectura directa de archivos en sesion activa

---

## PROTOCOLO DE LECTURA PARA OTRA IA

Este documento describe **codigo real verificado** en esta sesion. Cada afirmacion esta respaldada
por lectura directa de archivos. Donde hay incertidumbre, se usa `[VERIFICAR]`.

**Regla de uso:** Si vas a modificar algo descrito aqui, lee el archivo original antes de hacerlo.
Este documento puede quedar desfasado. Los archivos siempre son la fuente de verdad.

---

## 1. PROPOSITO DEL SISTEMA

**TravelHub** es un CRM/ERP SaaS B2B multi-tenant para **agencias de viajes venezolanas**. Cada
instancia de cliente (agencia) corre en el mismo servidor Django pero con datos 100% aislados
mediante Row-Level Security (RLS) a nivel de ORM y PostgreSQL.

### Modelo de negocio SaaS

| Plan       | Usuarios | Ventas/mes | Storage    |
|------------|----------|------------|------------|
| FREE       | 1        | 20         | 100 MB     |
| BASIC      | 2        | 50         | 500 MB     |
| PRO        | 10       | 500        | 5 GB       |
| ENTERPRISE | 999      | ilimitado  | ilimitado  |

> Definido en `travelhub/settings/base.py:527-537` — `SAAS_PLAN_LIMITS`

### Flujo de dinero (Stripe)

El sistema tiene la **infraestructura Stripe configurada** (`stripe_customer_id`,
`stripe_subscription_id` en `AgenciaConfiguracion`; variables `STRIPE_PRICE_ID_BASIC/PRO/ENTERPRISE`
en settings) pero **[VERIFICAR]** el flujo completo de checkout a webhook a activacion de plan.
Se detecto riesgo activo en `TECH_DEBT_REMEDIATION.md P0-005`: los webhooks Stripe pueden no
estar validando firma en todos los endpoints.

Lo que SI esta verificado:
- `AgenciaConfiguracion.plan` (CharField, default `"FREE"`) controla el plan activo
- `AgenciaConfiguracion.plan_status` controla estado (`active`, etc.)
- `AgenciaConfiguracion.fecha_fin_trial` se auto-asigna a `now() + 14 dias` al crear configuracion
- El middleware `SaaSLimitMiddleware` (`core/middleware_saas.py`) aplica throttling por plan en cada request

---

## 2. GLOSARIO DE DOMINIO

| Termino              | Definicion |
|----------------------|-----------|
| **Agencia**          | Tenant. Una empresa agencia de viajes. Tiene su propio plan SaaS, usuarios, datos y branding. |
| **GDS**              | Global Distribution System. Software de emision de boletos. TravelHub soporta: KIU, Sabre, Amadeus (WIP), Copa SPRK, Estelar Web, Rutaca Web. |
| **PNR**              | Passenger Name Record. Codigo de reserva de 6 caracteres alfanumericos (ej: WPYVSD). Asignado por el GDS. |
| **Boleto**           | E-ticket electronico emitido por el GDS. Tiene numero de 13 digitos (ej: 1347258019382). |
| **Fee de agencia**   | Comision o cargo de servicio que la agencia cobra al cliente sobre el precio base del boleto. |
| **Boleto de tercero**| Boleto emitido por otro proveedor (aerolinea directa, OTA) que la agencia importa al sistema para gestionar el servicio. |
| **Diferencial cambiario** | Ganancia que la agencia obtiene al cobrar en USD al mercado paralelo y liquidar al proveedor a la tasa BCV. Logica critica venezolana. |
| **IGTF**             | Impuesto a las Grandes Transacciones Financieras (Venezuela). Se aplica sobre pagos en divisa extranjera. |
| **BCV**              | Banco Central de Venezuela. El sistema sincroniza tasas USD/VES 2x/dia via `core.tasks.sync_bcv_rates`. |
| **Localizador aerolinea** | Secondary PNR asignado por la aerolinea operadora (distinto del PNR del GDS). |
| **RIF**              | Registro de Informacion Fiscal. Equivalente venezolano al NIT/RFC. Campo obligatorio en facturas. |
| **Venta**            | Unidad de negocio central. Contiene uno o mas items (boletos, hoteles, autos, servicios). |
| **ItemVenta**        | Linea dentro de una Venta. Puede ser un BoletoImportado u otro servicio. |
| **Liquidacion**      | Proceso de pago al proveedor. Calcula tarifa neta vs. lo cobrado al cliente. |
| **White-label**      | Personalizacion de la plataforma con marca propia de la agencia (logo, colores, dominio). |
| **Evolution API**    | Microservicio de WhatsApp (v2.2.3). Cada agencia tiene su instancia auto-provisionada. |
| **Mailbot**          | Monitor IMAP que lee el correo de emisiones de la agencia y detecta boletos entrantes automaticamente. |

---

## 3. STACK TECNOLOGICO EXACTO

### Backend
```
Python:          [VERIFICAR -- no inspeccionado .python-version; probablemente 3.11+]
Django:          5.2.14  (requirements/base.txt:3)
DRF:             3.15.2  (djangorestframework)
Celery:          5.5.3
PostgreSQL:      15-alpine (docker-compose.yml:40)
Redis:           7-alpine  (docker-compose.yml:95)
PgBouncer:       edoburu/pgbouncer (connection pooler, transaction mode)
```

### Librerias clave (requirements/base.txt)
```
cryptography:      46.0.7   -- Fernet para EncryptedCharField/EncryptedTextField
google-genai:      1.59.0   -- SDK oficial de Google AI (Gemini)
openai:            2.48.0   -- Proveedor fallback (ProviderChain)
PyMuPDF:           1.26.3   -- Extraccion de texto PDF (fitz)
weasyprint:        68.0     -- Generacion de PDF desde HTML
stripe:            13.0.1   -- Pagos SaaS
django-axes:       7.0.1    -- Proteccion brute-force
django-unfold:     0.91.0   -- Admin UI premium
django-waffle:     4.1.0    -- Feature flags
amadeus:           12.0.0   -- SDK aerolinea Amadeus [VERIFICAR integracion activa]
sentry-sdk:        2.50.0   -- Error tracking en produccion
django-prometheus: 2.3.1    -- Metricas /prometheus/
```

### Frontend
```
Motor:        Django Templates + HTMX + Alpine.js
Alpine.js:    v2/v3 (archivo local en raiz del proyecto)
Tailwind CSS: CDN (no compilado localmente)
Admin:        django-unfold (dark mode)
```

### Variables de entorno obligatorias

| Variable                          | Proposito |
|-----------------------------------|-----------|
| SECRET_KEY                        | Clave maestra Django (min 50 chars en prod) |
| ENCRYPTION_KEY                    | Clave Fernet para campos cifrados |
| DATABASE_URL                      | PostgreSQL connection string |
| REDIS_URL                         | Redis (broker Celery + cache) |
| GEMINI_API_KEY                    | API key de Google AI Studio (fallback global) |
| STRIPE_SECRET_KEY                 | Clave secreta Stripe (pagos SaaS) |
| STRIPE_WEBHOOK_SECRET             | Secret para verificar firmas de webhooks Stripe |
| STRIPE_PRICE_ID_BASIC/PRO/ENTERPRISE | IDs de precios en Stripe |
| R2_ACCESS_KEY_ID                  | Credencial Cloudflare R2 |
| R2_SECRET_ACCESS_KEY              | Credencial Cloudflare R2 |
| R2_BUCKET_NAME                    | Bucket de medios |
| R2_ENDPOINT_URL                   | Endpoint R2 |
| WHATSAPP_MICROSERVICE_URL         | URL de Evolution API |
| WHATSAPP_MICROSERVICE_TOKEN       | Token global de Evolution API |
| EVOLUTION_INSTANCE_TOKEN          | Token de instancia Evolution |
| RESEND_API_KEY                    | API key de Resend (emails transaccionales) |
| SENTRY_DSN                        | DSN de Sentry para error tracking |
| JWT_SIGNING_KEY                   | Clave firma JWT |
| TELEGRAM_BOT_TOKEN                | Bot de Telegram para notificaciones internas |
| TELEGRAM_ADMIN_ID                 | Chat ID del administrador del sistema |
| GCP_JSON_CREDENTIALS              | Credenciales Google Cloud |
| USE_PGBOUNCER                     | true/false -- activa CONN_MAX_AGE=0 para RLS-safe |
| DATABASE_REPLICA_URL              | URL replica PostgreSQL |
| GOTENBERG_URL                     | Servicio Gotenberg para PDF headless |
| BINANCE_PAY_API_KEY               | Pagos con Binance Pay |
| ENVIRONMENT                       | production/development |
| GIT_SHA                           | SHA del commit actual (para Sentry release) |

---

## 4. INFRAESTRUCTURA Y DEPLOY

### Produccion

```
Dominio principal:  travelhub.cc
Hosting:            [VERIFICAR -- probablemente VPS con Docker]
Proxy:              Traefik v3.0 (Let's Encrypt automatico via CF_DNS_API_TOKEN)
Base de datos:      PostgreSQL 15-alpine (contenedor Docker interno)
Cache/Broker:       Redis 7-alpine (contenedor Docker interno)
Pool de conexiones: PgBouncer (transaction mode, MAX_CLIENT_CONN=100, DEFAULT_POOL_SIZE=25)
Media:              Cloudflare R2 (USE_R2=True en produccion)
Estaticos:          WhiteNoise (servidos por Gunicorn/Django directamente)
PDF headless:       Gotenberg (contenedor separado, http://gotenberg:3000)
WhatsApp:           Evolution API v2 (contenedor evolution, puerto 8080)
Monitoring:         Sentry + Prometheus /prometheus/ + OpenTelemetry
```

### Servicios Docker (docker-compose.yml)
```
traefik        -> Proxy + SSL (red: travelhub_public)
db             -> PostgreSQL 15 (red: travelhub_private)
pgbouncer      -> Connection pooler (red: travelhub_private)
redis          -> Broker/cache (red: travelhub_private)
web            -> Django + Gunicorn (WSGI)
celery-worker  -> Worker asincrono (cola default + notifications)
celery-beat    -> Scheduler de tareas programadas
evolution      -> WhatsApp Evolution API v2
```

### Deploy local (desde cero)
```bash
git clone <repo>
cd travelhub_project
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements/base.txt -r requirements/dev.txt
cp .env.example .env.local  # Editar con valores reales
python manage.py migrate
python manage.py createsuperuser
DJANGO_SETTINGS_MODULE=travelhub.settings.development python manage.py runserver
# En otra terminal:
celery -A travelhub worker -l info
celery -A travelhub beat -l info
```

---

## 5. MAPA DE ARCHIVOS CRITICOS

```
travelhub_project/
|
+-- travelhub/                     <- Config del proyecto Django
|   +-- settings/
|   |   +-- base.py                <- MIDDLEWARE, APPS, SAAS_PLAN_LIMITS, JWT, DATABASES
|   |   +-- production.py          <- HSTS, SSL, Sentry, validaciones estrictas de secrets
|   |   +-- development.py         <- Debug tools, email console
|   |   +-- testing.py             <- Overrides para pytest
|   +-- urls.py                    <- Router maestro (todas las rutas)
|   +-- urls_api.py                <- Router DRF (merge bookings + crm + finance routers)
|   +-- celery.py                  <- Configuracion Celery app
|   +-- celery_beat_schedule.py    <- Tareas programadas (crontab)
|
+-- core/                          <- App nucleo (SaaS, multi-tenancy, seguridad)
|   +-- middleware.py              <- ThreadLocalContextMiddleware (L137),
|   |                                 MultiTenantDomainMiddleware (L500),
|   |                                 SecurityHeadersMiddleware + CSP dinamico (L354)
|   +-- middleware_saas.py         <- SaaSLimitMiddleware (throttling por plan)
|   +-- middleware_ai_ratelimit.py <- Rate limiting endpoints IA
|   +-- middleware_onboarding.py   <- Redirect al onboarding si agencia incompleta
|   +-- middleware_plan_limits.py  <- Enforcement limites de plan por accion
|   +-- security.py                <- get_agencia_or_403, get_object_tenant_or_404,
|   |                                 filter_queryset_by_tenant, agency_role_required (L122)
|   +-- mixins.py                  <- SaaSMixin (CBV queryset filter + RBAC),
|   |                                 AgencyRoleRequiredMixin, HtmxResponseMixin
|   +-- fields.py                  <- EncryptedCharField, EncryptedTextField (Fernet, L24-142)
|   +-- signals.py                 <- Signals de negocio (parseo automatico boletos)
|   +-- signals_audit.py           <- Signals de auditoria (AuditLog automatico)
|   +-- db_router.py               <- PrimaryReplicaRouter (reads->replica, writes->default)
|   +-- tasks.py                   <- Tareas Celery de core (sync_bcv, process_emails, etc.)
|   +-- models/
|       +-- __init__.py            <- Exports publicos de core.models
|       +-- base.py                <- AgenciaMixin (L197), AgenciaManager (L48),
|       |                             SaasQuerySet, SoftDeleteModel,
|       |                             GlobalAwareAgenciaManager, SoftDeleteQuerySet
|       +-- agencia.py             <- Agencia (L15), UsuarioAgencia (L374),
|       |                             AgenciaBranding (L410), AgenciaConfiguracion (L472)
|       +-- audit.py               <- AuditLog (L16) -- hash-chained, forense
|       +-- ai.py                  <- AIUsageLog (L6) -- tracking de costos IA
|       +-- api_keys.py            <- Modelo de API keys externas
|       +-- webhooks.py            <- Webhook, WebhookDelivery, WebhookEvent
|
+-- apps/                          <- Modulos de negocio (Django apps)
|   +-- bookings/                  <- Core de ventas y boletos
|   |   +-- models/
|   |   |   +-- venta.py           <- Venta, ItemVenta, PagoVenta, FeeVenta
|   |   |   +-- importacion.py     <- BoletoImportado (estado_parseo, archivo_pdf_generado)
|   |   |   +-- servicios.py       <- Reservas de hotel, auto, seguros
|   |   |   +-- componentes.py     <- Componentes adicionales de venta
|   |   +-- tasks.py               <- retry_queued_boletos_task
|   |   +-- serializers.py         <- DRF serializers (39KB -- el mas grande del proyecto)
|   |   +-- signals.py             <- Signals de bookings (PDF, venta, etc.)
|   |
|   +-- automation/                <- Motor IA y parseo de documentos
|   |   +-- parsers/
|   |   |   +-- ticket_parser.py   <- FastDeterministicParsers (regex), extract_data_from_text (L306)
|   |   |   +-- gemini_parser.py   <- GeminiParser (NLP + Vision para PDFs corruptos)
|   |   |   +-- kiu_parser.py      <- Parser especifico KIU (GDS venezolano) [28799 bytes]
|   |   |   +-- base_parser.py     <- BaseTicketParser, ParsedTicketData [31060 bytes]
|   |   |   +-- adapter.py         <- parse_ticket_with_new_parsers (router de parsers)
|   |   |   +-- normalization.py   <- CatalogNormalizationService (aeropuertos, aerolineas)
|   |   |   +-- pdf_generation.py  <- PdfGenerationService (Gotenberg/WeasyPrint)
|   |   +-- services/
|   |   |   +-- ai_engine.py       <- AIEngine.call_gemini() (L86), get_gemini_api_key() (L44)
|   |   |   +-- ai_router.py       <- ProviderChain (Gemini -> OpenAI -> DeepSeek fallback)
|   |   |   +-- ticket_parser_service.py <- TicketParserService [44700 bytes -- orquestador]
|   |   |   +-- ai_agent.py        <- Agente conversacional con Function Calling
|   |   |   +-- ai_copywriter.py   <- Generador de contenido marketing con IA
|   |   |   +-- ai_tools.py        <- Herramientas/Functions para el AI Agent [37637 bytes]
|   |   +-- tasks.py               <- process_web_uploaded_ticket, ejecutar_cobranza_ia_task
|   |
|   +-- finance/                   <- Contabilidad y facturacion
|   +-- crm/                       <- Clientes, pasaportes, pipeline Kanban
|   +-- contabilidad/              <- Plan de cuentas, asientos contables
|   +-- communications/            <- WhatsApp (Evolution), Telegram, Push
|   +-- common/                    <- Utilidades compartidas, SaaSQuotaService
|   +-- marketing/                 <- Campanias, leads, funnel
|   +-- reports/                   <- Reportes programados, exportacion
|   +-- cms/                       <- Contenido generado por IA
|   +-- cotizaciones/              <- Modulo de presupuestos/cotizaciones
|   +-- gamification/              <- [VERIFICAR alcance actual]
|   +-- tasks/                     <- Gestion de tareas internas de agencia
|
+-- templates/                     <- Templates globales
+-- static/                        <- Assets estaticos
+-- fixtures/                      <- Datos iniciales
+-- docker-compose.yml             <- Produccion (Traefik + PgBouncer + Evolution)
+-- docker-compose.dev.yml         <- Desarrollo local
+-- Dockerfile                     <- Imagen Django + Gunicorn
+-- .env.example                   <- Template de variables de entorno (137 vars)
+-- TECH_DEBT_REMEDIATION.md       <- Inventario de deudas tecnicas con prioridades P0-P4
+-- CONTEXT_MAP.md                 <- Este archivo
```

---

## 6. LOGICA DE MULTI-TENANCY

### Arquitectura de 4 capas (defense-in-depth)

**CAPA 1: MultiTenantDomainMiddleware (core/middleware.py:500)**
- Resuelve la agencia por dominio personalizado o subdominio
- Inyecta request.agencia / request.agency
- Lanza Http404 si el dominio no corresponde a ninguna agencia

**CAPA 2: ThreadLocalContextMiddleware (core/middleware.py:137)**
- Lee request.user -> busca UsuarioAgencia -> extrae Agencia
- Resuelve impersonacion God Mode (superuser, timeout 30 min)
- Inyecta en Python ContextVars: agency_var, user_var, etc.
- Ejecuta `SET LOCAL app.current_agencia_id = %s` en PostgreSQL
- Ejecuta `SET LOCAL app.bypass_rls = 'true'` para /admin/
- Limpieza garantizada en bloque finally

**CAPA 3: AgenciaManager.get_queryset() (core/models/base.py:63)**
- `Model.objects.all()` auto-filtra por agency_var
- Si `is_system_context()` -> bypass (Celery, tareas de fondo)
- Si superuser -> queryset completo (God Mode)
- Si no hay agencia + no superuser -> `queryset.none()`
- Aplica tambien soft-delete (is_deleted=False)

**CAPA 4: SaaSMixin / get_object_tenant_or_404 (CBV + Func Views)**
- get_queryset() con filtro agencia explicito (redundancia)
- RBAC por rol (vendedor ve solo sus propias ventas)
- Previene modificar en rol "consulta" o "contador"

### Codigo real -- AgenciaMixin (core/models/base.py:197)
```python
class AgenciaMixin(models.Model):
    agencia = models.ForeignKey("core.Agencia", ...)
    objects = AgenciaManager()       # filtra automaticamente por tenant
    all_objects = models.Manager()   # sin filtro (admin/sistema)
    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        # Auto-asigna agencia desde ContextVar si no esta presente
        # Levanta PermissionDenied si hay cruce de datos cross-tenant
        ...
```

### Codigo real -- AgenciaManager (core/models/base.py:48)
```python
def get_queryset(self):
    if is_system_context(): return queryset   # Celery bypass
    agency = get_current_agency()             # Lee ContextVar
    if agency: return queryset.filter(agencia=agency)  # CLAVE
    if user and user.is_superuser: return queryset
    return queryset.none()  # Seguridad por defecto
```

### Contexto de sistema para Celery tasks
```python
from core.middleware import system_context, agency_context

# Tarea cross-tenant:
with system_context(reason="retry_queued_boletos", max_seconds=60.0):
    BoletoImportado.all_objects.filter(...).update(...)

# Tarea por agencia especifica:
with agency_context(agencia):
    BoletoImportado.objects.filter(estado_parseo="EN_PROCESO")
```

### Roles de usuario (UsuarioAgencia.rol)

| Rol        | Permisos |
|------------|----------|
| admin      | Todo |
| gerente    | Todo excepto configuracion SaaS |
| vendedor   | Solo sus propias ventas |
| contador   | Solo modelos financieros (Factura, PagoVenta, etc.) |
| operador   | Operacional sin finanzas |
| consulta   | Solo lectura, sin crear/modificar |

### Impersonacion God Mode
Un superuser puede impersonar cualquier agencia desde el admin.
Token guardado en `request.session["impersonated_agencia_id"]` con timestamp.
**Timeout automatico: 30 minutos** (timedelta(seconds=1800) en middleware.py:202).

---

## 7. ARQUITECTURA DE LA IA INTERNA

### 7.1 Ticket Parser Pro (parseo de boletos)

Flujo de procesamiento:
```
ARCHIVO SUBIDO (PDF/TXT/EML)
         |
         v
TicketParserService.procesar_boleto()
         |
         +-- Extraccion de texto
         |    +-- PyMuPDF (fitz) para PDF
         |    +-- Decodificacion EML para correos
         |
         +-- MOTOR 1: GDS Especifico (Deterministico / Gratis)
         |    +-- adapter.parse_ticket_with_new_parsers()
         |         +-- KiuParser      (kiu_parser.py -- boletos KIU)
         |         +-- ConsoleParser  (console_parser.py -- formato consola GDS)
         |         +-- [otros parsers registrados en registry.py]
         |
         +-- MOTOR 2: Regex Generico (FastDeterministicParsers)
         |    +-- extract_data_from_text() en ticket_parser.py
         |         +-- SHA-256 fingerprint -> cache Redis (TTL 86400s)
         |         +-- Patrones regex para PNR, boleto, nombre, vuelos
         |
         +-- MOTOR 3: IA (GeminiParser) [mas costoso]
              +-- GeminiParser.parse(text, html_text, pdf_path)
                   +-- Modelo: gemini-2.5-flash
                   +-- Timeout: 20 segundos (ThreadPoolExecutor)
                   +-- Vision: activa si texto corrupto "(cid:" o < 100 chars
                   +-- Fallback: devuelve {} en error
```

Orden de prioridad en extract_data_from_text() (ticket_parser.py:306-375):
1. Cache Redis (fingerprint SHA-256, TTL 24h)
2. parse_ticket_with_new_parsers() -- parsers GDS especificos
3. FastDeterministicParsers.parse_general_regex() -- regex generico
4. Si todo falla -> retorna dict vacio (no lanza excepcion)

Tarea Celery del parseo (apps/automation/tasks.py:8):
```python
@shared_task(bind=True, max_retries=3, soft_time_limit=20, time_limit=30)
def process_web_uploaded_ticket(self, boleto_id, agencia_id=None):
    # Estados: EN_PROCESO -> COMPLETADO | REVISION_REQUERIDA
    # SoftTimeLimitExceeded -> marca REVISION_REQUERIDA (no crashea)
```

### 7.2 AI Engine (motor unificado)

```python
# apps/automation/services/ai_engine.py
class AIEngine:
    DEFAULT_MODEL = "gemini-2.5-flash"
    PRO_MODEL     = "gemini-1.5-pro"

    def call_gemini(self, prompt, content_list=None, response_schema=None, ...):
        # Delega a ProviderChain con fallback automatico:
        # Gemini -> OpenAI -> DeepSeek
```

Resolucion de API key (prioridad):
1. `AgenciaConfiguracion.gemini_api_key` -- clave privada de la agencia (cifrada con Fernet)
2. `os.environ["GEMINI_API_KEY"]` -- clave global del sistema

Esto permite que cada agencia PRO/ENTERPRISE use su propia cuota de Gemini.

### 7.3 AI Agent con Function Calling

```
apps/automation/services/ai_agent.py       (6497 bytes)
apps/automation/services/ai_tools.py       (37637 bytes -- herramientas Function Calling)
```

Agente conversacional. Las herramientas en ai_tools.py permiten al agente ejecutar acciones reales
del ERP (consultar ventas, crear boletos, etc.).
[VERIFICAR] integracion con WhatsApp chatbot.

### 7.4 Control de costos IA

```python
# core/models/ai.py
class AIUsageLog(models.Model):
    agencia        = ForeignKey(Agencia)
    model_name     = CharField  # 'gemini-2.5-flash', 'gemini-1.5-pro'
    feature        = CharField  # 'ticket_parsing', 'reconciliation', 'marketing_copy'
    input_tokens   = IntegerField
    output_tokens  = IntegerField
    estimated_cost = DecimalField(max_digits=10, decimal_places=6)
    status         = CharField  # 'SUCCESS', 'FAILED', '429_LIMIT'
```

Rate limiting via core/middleware_ai_ratelimit.py:
- ai_parser_quota: 20/minute
- ai_parser_daily: 200/day

---

## 8. CONTRATO DE API / ENDPOINTS PRINCIPALES

### Autenticacion

| Metodo | Ruta | Proposito | Auth |
|--------|------|-----------|------|
| POST | /api/auth/jwt/obtain/ | Obtener JWT access + refresh tokens | No |
| POST | /api/auth/jwt/logout/ | Invalidar refresh token | Token |
| GET | /auth/magic-request/ | Solicitar magic link por email | No |
| GET | /auth/magic/<token>/ | Verificar y autenticar con magic link | No |
| POST | /login/ | Login clasico Django (session) | No |
| POST | /sso/login/<provider_id>/ | Inicio SSO/OIDC | No |

### API REST (todas requieren Token o JWT)

| Metodo | Ruta | Proposito |
|--------|------|-----------|
| GET/POST | /api/boletos/ | Listar / crear BoletoImportado |
| POST | /api/boletos/upload/ | Subir PDF/TXT para parseo automatico |
| POST | /api/boletos/<pk>/retry-parse/ | Re-parsear boleto existente |
| GET/POST | /api/ventas/ | CRUD de Ventas |
| GET/POST | /api/facturas/ | CRUD de Facturas |
| GET/POST | /api/clientes/ | CRUD CRM -- Clientes |
| GET | /api/dashboard/stats/ | KPIs del dashboard (throttle: 100/hour) |
| GET | /api/tasas-bcv/ | Tasas de cambio BCV actuales |
| GET | /api/audit-logs/ | Logs de auditoria (solo staff) |
| POST | /api/parse-demo/ | Demo publico de parseo de boleto |
| GET | /api/schema/ | OpenAPI schema (solo staff en prod) |
| GET | /api/docs/ | Swagger UI (solo staff en prod) |

### Sistema y monitoreo

| Metodo | Ruta | Auth |
|--------|------|------|
| GET | /health/ | No |
| GET | /health/metrics/ | No |
| GET | /prometheus/ | No |
| POST | /csp-report/ | No (CSRF exempt) |
| GET | /status/ | Staff only |

### Webhooks externos (CSRF exempt, verificacion de firma requerida)

| Metodo | Ruta | Proposito |
|--------|------|-----------|
| POST | /system/webhooks/stripe/ | Eventos Stripe (billing) |
| POST | /system/webhooks/whatsapp/ | Mensajes WhatsApp Meta Cloud API |
| GET/POST | /system/webhooks/telegram/ | Updates bot Telegram |
| POST | /system/webhooks/binance/ | Confirmaciones pago Binance Pay |

---

## 9. SEGURIDAD Y REGLAS DE ORO

### Medidas implementadas (verificadas en codigo)

#### Cifrado en campo (core/fields.py)
- EncryptedCharField y EncryptedTextField usan Fernet (AES-128-CBC + HMAC-SHA256)
- Campos cifrados en AgenciaConfiguracion: password_app_correo, telegram_bot_token,
  evolution_api_key, email_monitor_password, gemini_api_key
- Deteccion de doble cifrado: si valor empieza con 'gAAAAA', no se vuelve a cifrar
- Fallo en descifrado -> retorna "" + loguea a Sentry (no crashea la app)

#### Proteccion brute-force (django-axes, verificado en settings/base.py)
```python
AXES_ENABLED = True
AXES_FAILURE_LIMIT = 5       # Bloqueo tras 5 intentos fallidos
AXES_COOLOFF_TIME = 1        # Hora de cooldown
AXES_LOCKOUT_PARAMETERS = ["username", "ip_address"]
AXES_RESET_ON_SUCCESS = True
```

#### JWT (verificado en settings/base.py)
```python
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "ALGORITHM": "HS256",
}
```

#### Sesiones (verificado en settings/base.py)
```python
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_AGE = 14400      # 4 horas
SESSION_COOKIE_NAME = "th_sessionid"
CSRF_COOKIE_NAME = "th_csrftoken"
SESSION_COOKIE_SAMESITE = "Lax"
```

#### Content Security Policy dinamico (verificado en core/middleware.py:354)
- Generado por SecurityHeadersMiddleware en cada request
- Nonce criptografico unico por request (secrets.token_hex(16))
- Cada agencia puede extender CSP via AgenciaConfiguracion.csp_directives (JSONField)
- Headers adicionales: X-Content-Type-Options: nosniff,
  Referrer-Policy: strict-origin-when-cross-origin, X-Frame-Options: DENY

#### RLS a nivel de base de datos (verificado en core/middleware.py)
```sql
-- Ejecutado por ThreadLocalContextMiddleware en cada request:
SET LOCAL app.current_agencia_id = '<id>';
SET LOCAL app.bypass_rls = 'false';
-- Al finalizar el request (bloque finally garantizado):
SET LOCAL app.current_agencia_id = '0';
SET LOCAL app.bypass_rls = 'false';
```
Con ATOMIC_REQUESTS = True, estas variables tienen el mismo ciclo de vida que la transaccion.

#### Audit Log forense (core/models/audit.py:16)
- Cadena de hashes (blockchain-style): previous_hash y record_hash (SHA-256) en cada registro
- Inmutable: no se borra, solo SET_NULL en FK si la Venta es eliminada
- Registra: CREATE, UPDATE, DELETE, STATE, LOGIN, LOGOUT

#### DB Router (core/db_router.py)
- PrimaryReplicaRouter: reads -> replica, writes -> default
- apps criticas (axes, sessions, admin) siempre al primary
- En tests: usa 'default' como espejo de 'replica'

### Reglas de ORO (nunca violar)

```
[CRITICO] REGLA 1: NUNCA hacer Model.objects.get(pk=pk) sin filtro de agencia en vistas de usuario.
  Correcto: get_object_tenant_or_404(Model, agencia, pk=pk)
  Correcto: Model.objects.get(pk=pk, agencia=agencia)

[CRITICO] REGLA 2: NUNCA usar SQL crudo (cursor.execute) para manipular entidades de negocio.
  Solo Django ORM: objects.create(), objects.filter(), transaction.atomic()

[CRITICO] REGLA 3: NUNCA inventar librerias. Si no esta en requirements/base.txt, no usarla.

[CRITICO] REGLA 4: NUNCA guardar secretos en codigo fuente.
  Solo en variables de entorno o EncryptedCharField en la base de datos.

[ALTO] REGLA 5: Todo modelo de negocio DEBE heredar AgenciaMixin.
  Esto garantiza el filtro automatico del AgenciaManager.

[ALTO] REGLA 6: Para tareas Celery cross-tenant, usar SIEMPRE system_context(reason="...").
  El parametro reason es obligatorio para auditoria.

[ALTO] REGLA 7: No activar USE_PGBOUNCER=True sin tambien configurar CONN_MAX_AGE=0.
  Con PgBouncer en transaction mode + CONN_MAX_AGE>0, el RLS se fuga entre requests.

[MEDIO] REGLA 8: Validar entidades en modelos (validators.py), no en vistas.
  Las vistas solo convierten request -> model -> response.

[MEDIO] REGLA 9: Ciudades/origenes en parseo Sabre: usar [\t ] (horizontal) no \s en regex.
  \s incluye saltos de linea y desplaza el match. (Ver .agents/AGENTS.md)

[MEDIO] REGLA 10: core/ NO puede importar de apps/*. Solo apps/* importan de core/.
  Si necesitas logica de apps/ en core/, usa referencias lazy ('app.ModelName').
```

---

## 10. BUGS Y LIMITACIONES CONOCIDAS

> Deuda técnica reconocida. No estan en trabajo activo.
> Ver TECH_DEBT_REMEDIATION.md para inventario completo.

### P0 — Seguridad (critico) — ✅ TODOS RESUELTOS

| ID | Descripcion | Estado |
|----|------------|--------|
| P0-002 | IDOR en BoletoRetryParseAPIView | ✅ RESUELTO — `get_object_tenant_or_404()` en boleto_views.py:165 |
| P0-003 | IDOR en VentaDoubleInvoiceAPIView | ✅ RESUELTO — `get_object_tenant_or_404()` en boleto_views.py:365 |
| P0-005 | Webhook Stripe sin firma | ✅ RESUELTO — `stripe.Webhook.construct_event()` en views_webhooks.py:159 |
| P0-006 | Information Disclosure str(e) | ✅ RESUELTO — todos reemplazados con error_id + logger.exception |

### P1 — Estabilidad — ✅ TODOS RESUELTOS

| ID | Descripcion | Estado |
|----|------------|--------|
| P1-001 | Doble signal post_save | ✅ RESUELTO — un solo receiver verificado |
| P1-002 | django.setup() en celery.py | ✅ RESUELTO — no existe llamada explicita |

### Limitaciones de parseo de boletos

- PDFs con texto codificado como imagen (boletos Avior Web): requiere Gemini Vision, con costo y latencia
- Boletos Amadeus: parser generico regex; sin parser especifico (stub sin implementar)
- Variabilidad de formatos KIU: funciona para aerolineas venezolanas principales, puede fallar en otras
- Timeout de Gemini: 20 segundos. Boletos complejos o red lenta -> REVISION_REQUERIDA

---

## 11. BRECHAS EN REPARACION

> Estado al 2026-07-26 en rama `hardening/operational-risks`

| ID | Descripcion | Estado |
|----|------------|--------|
| P0-004 | system_context() sin limite de tiempo | OK -- max_seconds=60.0 en middleware.py:69 |
| P1-003 | CONN_MAX_AGE incompatible con PgBouncer | OK -- USE_PGBOUNCER env var en base.py |
| P2-006 | Re-evaluacion de sys.argv en cada query | OK -- constantes _IS_PYTEST, _IS_MANAGEMENT_COMMAND |
| P0-002 | IDOR BoletoRetryParseAPIView | OK -- get_object_tenant_or_404() |
| P0-003 | IDOR VentaDoubleInvoiceAPIView | OK -- get_object_tenant_or_404() |
| P0-005 | Stripe webhook firma | OK -- construct_event() validado |
| P0-006 | Traceback en 500 | OK -- error_id pattern |
| P1-001 | Doble signal BoletoImportado | OK -- un solo receiver |
| P1-002 | django.setup() en celery.py | OK -- no existe |
| P1-004 | Cache TTL agencia | OK -- 30s + signal invalidacion |
| P1-005 | locale.setlocale global | OK -- safe_setlocale en core/locale_patch.py |
| P1-006 | Truncacion silenciosa | OK -- log + flag |
| P1-007 | WhatsApp sync en signals | OK -- .delay() |
| P2-001 | Comentario placeholder | OK -- no existe |
| P2-003 | flights SDK sin uso | OK -- eliminado de requirements |
| P2-005 | GDS months duplicado | OK -- centralizado |
| P2-007 | @property id | OK -- eliminado |
| P2-008 | Tests en raiz | OK -- movidos a scratch_scripts/ |
| P2-009 | _build_redis_url en settings | OK -- movido a core/utils/redis_utils.py |
| P2-011 | Nested atomic en Venta.save() | OK -- select_for_update() |
| P3-001 | Boletos QUE nunca reintentados | OK -- retry_queued_boletos_task existe |
| P3-004 | log_parseo sin limite | OK -- truncado a 4000 chars en save() |
| Contabilidad IA | AsientoContableSchema refactorizado | OK -- Resuelto |
| Parser Amadeus | Implementacion real del parser Amadeus | PENDIENTE |
| P3-002 | Endpoint polling estado parseo | PENDIENTE |
| P3-003 | Alerta cuota Gemini por agencia | PENDIENTE |
| P4-001 | Metricas precision parser | PENDIENTE |
| P4-002 | God Object urls.py | PENDIENTE |
| P4-003 | Versionado datos_parseados | PENDIENTE |
| P4-004 | NotificationRouter unificado | PENDIENTE |
| P4-005 | CI/CD check documentacion | PENDIENTE |

---

## APENDICE: Patrones de codigo rapidos para nueva IA

### Nuevo endpoint REST seguro

```python
from core.api.mixins.tenant import TenantViewSetMixin  # [VERIFICAR path exacto]
from core.security import get_agencia_from_request, get_object_tenant_or_404

class MiModeloViewSet(TenantViewSetMixin, viewsets.ModelViewSet):
    serializer_class = MiModeloSerializer
    # get_queryset() ya filtra por agencia (via TenantViewSetMixin -> AgenciaManager)

    def get_object(self):
        agencia = get_agencia_from_request(self.request)
        return get_object_tenant_or_404(MiModelo, agencia, pk=self.kwargs["pk"])
```

### Nuevo modelo de negocio

```python
from core.models.base import AgenciaMixin, SoftDeleteModel

class MiModelo(AgenciaMixin, SoftDeleteModel):
    nombre = models.CharField(max_length=200)
    # agencia ForeignKey INCLUIDO automaticamente por AgenciaMixin
    # is_deleted, deleted_at INCLUIDO por SoftDeleteModel
    # objects (AgenciaManager) filtra por tenant automaticamente
    # all_objects (Manager) sin filtro para admin/sistema
    # with_deleted (SoftDeleteManager) incluye eliminados
    class Meta:
        app_label = "mi_app"
```

### Tarea Celery con contexto de agencia

```python
from celery import shared_task
from core.middleware import agency_context

@shared_task(bind=True, max_retries=3)
def mi_tarea(self, agencia_id):
    from core.models import Agencia
    agencia = Agencia.objects.get(pk=agencia_id)
    with agency_context(agencia, reason="mi_tarea_descripcion"):
        # Model.objects.all() filtra por agencia automaticamente aqui
        pass
```

### Acceder a IA con fallback automatico

```python
from apps.automation.services.ai_engine import AIEngine

engine = AIEngine()
result = engine.call_gemini(
    prompt="Tu prompt aqui",
    feature="mi_feature",       # Para AIUsageLog (tracking de costos)
    temperature=0.1,
    agency=request.agencia,     # Para resolver la API key correcta
)
if "error" in result:
    # El engine ya intento todos los proveedores del chain (Gemini -> OpenAI -> DeepSeek)
    pass
```

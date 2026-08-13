# CONTEXT_MAP.md — Mapa Cerebral de TravelHub

> **Última verificación contra código real:** 2026-08-13
> **Rama/commit revisado:** `main` @ `a226bd5911f590fafd0464c9e198e9b4d1b531e3`
> **Verificado por:** IA (Gemini 3.6 Flash) — lectura directa de archivos en sesión activa

---

## PROTOCOLO DE LECTURA PARA OTRA IA

Este documento describe **código real verificado** en esta sesión. Cada afirmación está respaldada por lectura directa de archivos en el repositorio `travelhub_project`. Donde hay incertidumbre o supuestos no confirmados directamente por lectura de código, se marca explícitamente con `[VERIFICAR]`.

**Regla de uso:** Si vas a modificar o construir sobre algún componente descrito aquí, lee el archivo fuente original primero. Este documento es la arquitectura mapeada; los archivos del repositorio son la fuente de verdad definitiva.

---

## 1. PROPÓSITO DEL SISTEMA

**TravelHub** es un CRM/ERP SaaS B2B multi-tenant diseñado para **agencias de viajes venezolanas**. Permite gestionar boletos aéreos (GDS KIU, Sabre, Amadeus), paquetes turísticos, hoteles, vehículos, alquileres, liquidación a proveedores con cálculo de diferencial cambiario (USD/VES a tasa BCV), facturación bimoneda con cumplimiento fiscal SENIAT e IGTF, y automatización multicanal (WhatsApp vía Evolution API y Telegram Bot).

Cada agencia consumidora del SaaS opera como un tenant aislado con su propia marca (white-label), usuarios, clientes, cotizaciones y estados financieros, compartiendo la misma infraestructura Django/PostgreSQL mediante **Row-Level Security (RLS)** y aislamiento a nivel de ORM.

### Modelo de negocio SaaS

El control de cuotas y límites por agencia está definido centralmente en `travelhub/settings/base.py:540-550`:

| Plan | Usuarios (`users`) | Almacenamiento (`storage_mb`) | Leads / mes (`leads_per_month`) | Ventas / mes (`sales_per_month`) |
| :--- | :--- | :--- | :--- | :--- |
| **FREE** | 1 | 100 MB | 20 | 20 |
| **BASIC** | 2 | 500 MB | 50 | 50 |
| **PRO** | 10 | 5.000 MB (5 GB) | 500 | 500 |
| **ENTERPRISE** | 999 | 99.999 MB | 99.999 | 99.999 |

Lógica de enforcement:
- El middleware `SaaSLimitMiddleware` (`core/middleware_saas.py`) intercepta las peticiones y throttling por plan.
- El servicio `SaaSQuotaService` (`apps/common/services/saas_limits.py`) valida límites de usuarios, almacenamiento y volumen mensual antes de permitir operaciones de creación.
- `AgenciaConfiguracion.fecha_fin_trial` asigna automáticamente 14 días de prueba al crear la configuración inicial (`core/models/agencia.py:472`).

### Flujo de pago y suscripciones (Stripe)

La integración con Stripe se gestiona a través de `StripeService` (`apps/finance/services/stripe_service.py`):
1. **Creación de Checkout Session**: `StripeService.create_checkout_session()` genera una sesión de pago para upgrades/downgrades de plan asociando la agencia vía `stripe_customer_id`.
2. **Customer Portal**: `StripeService.create_customer_portal_session()` permite a la agencia gestionar sus tarjetas y facturas directamente en Stripe.
3. **Webhooks Fail-Closed con Idempotencia**: El endpoint `/system/webhooks/stripe/` expuesto por `StripeWebhookView` (`apps/finance/views/views_webhooks.py:180`) valida obligatoriamente la firma HMAC con `stripe.Webhook.construct_event()`. Si falta el secret de webhook responde con `503`, y si la firma es inválida o ausente responde con `401`.
4. **Procesamiento de eventos**:
   - `customer.subscription.created` / `customer.subscription.updated`: Actualiza `AgenciaConfiguracion.plan` (FREE, BASIC, PRO, ENTERPRISE) y `plan_status` (`active`, `past_due`, `canceled`).
   - `customer.subscription.deleted`: Transiciona la agencia a plan `FREE` y `plan_status="canceled"`.
   - `invoice.payment_succeeded`: Renueva `fecha_fin_suscripcion`.
   - `invoice.payment_failed`: Marca el estado como `past_due` / `unpaid` para activar restricción de funciones avanzadas.

---

## 2. GLOSARIO DE DOMINIO

| Término | Definición |
| :--- | :--- |
| **Agencia** | Tenant. Entidad legal/comercial cliente del SaaS. Posee branding, usuarios, finanzas e instancias de mensajería aisladas. |
| **GDS** | *Global Distribution System*. Sistemas de emisión de pasajes. TravelHub soporta parseo de: KIU, Sabre, Amadeus, Copa SPRK, Estelar Web y Rutaca Web. |
| **PNR** | *Passenger Name Record*. Código de reserva alfanumérico de 6 caracteres (ej. `WPYVSD` o `4K3I2J`) asignado por el GDS. |
| **Boleto** | E-Ticket electrónico de 13 dígitos (ej. `1347258019382` o `139-2401829384`). Entidad `BoletoImportado`. |
| **Fee de agencia** | Comisión o cargo de servicio que la agencia añade sobre la tarifa neta del boleto/servicio. |
| **Boleto de tercero** | Pasaje emitido por consolidadores u otras agencias que se importa para gestión de cobro/itinerario. |
| **Diferencial cambiario** | Utilidad neta generada por la diferencia entre la tasa cobrada en divisa/mercado paralelo y la tasa oficial BCV a la que se liquida al proveedor. |
| **IGTF** | Impuesto a las Grandes Transacciones Financieras (3% en Venezuela sobre pagos en divisas/criptoactivos). |
| **BCV** | Banco Central de Venezuela. Tasa oficial USD/VES sincronizada automáticamente 2 veces al día por `core.tasks.sync_bcv_rates`. |
| **Localizador aerolínea** | PNR secundario emitido por la línea aérea operadora cuando difiere del PNR del GDS emisor. |
| **RIF** | Registro de Información Fiscal. Documento de identificación tributario en Venezuela (ej. `J-40249698-2`). |
| **Venta** | Entidad financiera y comercial agrupadora (`apps/bookings/models/venta.py:Venta`). Contiene `ItemVenta`, `PagoVenta`, `FeeVenta`. |
| **ItemVenta** | Línea de detalle dentro de una venta. Representa un boleto importado, hotel, vehículo o servicio adicional. |
| **Liquidación** | Proceso contable de cierre y pago hacia el proveedor de turismo, calculando comisiones y netos a pagar. |
| **White-label** | Capacidad del sistema para personalizar dominios, logos, colores primarios/secundarios y encabezados de PDF por agencia. |
| **Evolution API** | Microservicio externo REST/WebSocket (v2.2.3 en Docker) para integración directa con WhatsApp Web sin API Business oficial. |
| **Mailbot** | Worker asíncrono que monitorea casillas IMAP para procesar automáticamente e-tickets entrantes en PDF/HTML/EML. |

---

## 3. STACK TECNOLÓGICO EXACTO

### Backend & Core
- **Lenguaje:** Python 3.11.15
- **Framework Principal:** Django 5.2.14 (`requirements/base.txt:3`)
- **API REST:** Django REST Framework 3.15.2 (`requirements/base.txt:10`)
- **Tareas Asíncronas & Tareas Programadas:** Celery 5.5.3 + `django-celery-beat` 2.8.1 + `django-celery-results` 2.6.0
- **Base de Datos:** PostgreSQL 15-alpine (`docker-compose.yml:40`)
- **Cache & Message Broker:** Redis 7-alpine (`docker-compose.yml:95`)
- **Pool de Conexiones DB:** PgBouncer (modo `transaction`, `edoburu/pgbouncer`)

### Librerías Clave (`requirements/base.txt`)
```
cryptography==46.0.7       # Cifrado Fernet simétrico para campos sensibles
google-genai==1.59.0       # SDK oficial de Google Gemini (Gemini 2.5 Flash / Pro)
openai==2.48.0             # Fallback secundario en ProviderChain + DeepSeek HTTP compatibility
PyMuPDF==1.26.3            # Extracción rápida de texto/metadatos PDF (fitz)
pypdf==6.10.2              # Parser secundario de documentos estructurados
weasyprint==68.0           # Generador de PDF a partir de templates HTML/CSS
stripe==13.0.1             # SDK de pagos SaaS y gestión de suscripciones
django-axes==7.0.1         # Protección anti-bruteforce en autenticación
django-unfold==0.91.0      # Panel de administración Django moderno (UI Dark Mode)
django-waffle==4.1.0       # Feature Flags dinámicos
amadeus==12.0.0            # SDK oficial GDS Amadeus
sentry-sdk==2.50.0         # Monitoreo y reporte de excepciones en producción
django-prometheus==2.3.1   # Exposición de métricas en /prometheus/
python-telegram-bot==21.11 # Bot bidireccional y notificaciones de Telegram
opentelemetry-api==1.27.0  # Trazabilidad distribuida APM
defusedxml==0.7.1          # Parser seguro XML anti-XXE / Billion Laughs (retenciones SENIAT)
```

### Frontend
- **Arquitectura UI:** Django Server-Side Rendering (SSR) + HTMX + Alpine.js
- **Estilos CSS:** Tailwind CSS
- **Admin UI:** Django Unfold (con personalizaciones en `apps/common/urls_admin.py`)

### Variables de Entorno Obligatorias (`.env.example`)

| Variable | Propósito |
| :--- | :--- |
| `SECRET_KEY` | Clave criptográfica maestra de Django (mínimo 50 caracteres en producción). |
| `ENCRYPTION_KEY` | Clave Fernet base64 url-safe para `EncryptedCharField` y `EncryptedTextField`. |
| `DATABASE_URL` | String de conexión PostgreSQL (`postgres://user:pass@host:5432/dbname`). |
| `REDIS_URL` | String de conexión Redis (`redis://host:6379/0`) para broker Celery y cache. |
| `GEMINI_API_KEY` | API Key global de Google AI Studio para motor `AIEngine` / `UniversalAIParser`. |
| `STRIPE_SECRET_KEY` | Clave secreta de Stripe para cobros y Checkout Sessions. |
| `STRIPE_WEBHOOK_SECRET` | Secreto para verificación de firma HMAC de webhooks Stripe. |
| `STRIPE_PRICE_ID_BASIC/PRO/ENTERPRISE` | IDs de los planes configurados en Stripe Dashboard. |
| `R2_ACCESS_KEY_ID` / `R2_SECRET_ACCESS_KEY` | Credenciales de acceso a Cloudflare R2 Storage. |
| `R2_BUCKET_NAME` / `R2_ENDPOINT_URL` | Nombre del bucket y endpoint S3-compatible de Cloudflare R2. |
| `WHATSAPP_MICROSERVICE_URL` | URL base del microservicio Evolution API v2 (`http://evolution:8080`). |
| `WHATSAPP_MICROSERVICE_TOKEN` | Token de autenticación global para Evolution API. |
| `EVOLUTION_INSTANCE_TOKEN` | Token asignado a la instancia predeterminada de WhatsApp. |
| `RESEND_API_KEY` | API Key de Resend para envío de correos transaccionales. |
| `SENTRY_DSN` | URL DSN de Sentry para captura de errores en tiempo real. |
| `JWT_SIGNING_KEY` | Clave de firma para tokens JWT (`djangorestframework-simplejwt`). |
| `TELEGRAM_BOT_TOKEN` | Token HTTP API del bot de Telegram de la agencia / plataforma. |
| `TELEGRAM_ADMIN_ID` | Chat ID de Telegram para alertas críticas de sistema. |
| `USE_PGBOUNCER` | Flag `true`/`false`. Forza `CONN_MAX_AGE=0` para prevenir fugas de RLS. |
| `ALLOW_SYSTEM_CONTEXT` | Flag `1`/`true`. Permite ejecutar `system_context()` en tareas Celery. |
| `ENVIRONMENT` | Entorno de ejecución (`production` / `development` / `testing`). |

---

## 4. INFRAESTRUCTURA Y DEPLOY

### Topología de Producción (`docker-compose.yml`)

```
                        [ Cliente Web / Móvil ]
                                  │
                                  ▼
                      ┌──────────────────────┐
                      │    Traefik v3.0      │ (Reverse Proxy + SSL Let's Encrypt)
                      └──────────┬───────────┘
                                  │
         ┌────────────────────────┼────────────────────────┐
         │                        │                        │
         ▼                        ▼                        ▼
┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│  Django Web      │    │  Celery Worker   │    │   Celery Beat    │
│  (Gunicorn WSGI) │    │  (Async tasks)   │    │  (Cron Scheduler)│
└────────┬─────────┘    └────────┬─────────┘    └────────┬─────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
         ┌───────────────────────┼───────────────────────┐
         ▼                       ▼                       ▼
┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│    PgBouncer     │    │     Redis 7      │    │  Evolution API   │
│(Pool Transaction)│    │(Broker & Cache)  │    │  (WhatsApp v2)   │
└────────┬─────────┘    └──────────────────┘    └──────────────────┘
         │
         ▼
┌──────────────────┐
│  PostgreSQL 15   │ (RLS enabled on tenant tables)
└──────────────────┘
```

### Contenedores y Redes Docker
- **Proxy Inverso:** Traefik v3.0 en red `travelhub_public`.
- **Backend & Workers:** `web`, `celery-worker`, `celery-beat` en red `travelhub_private`.
- **Bases de Datos & Caching:** `db` (PostgreSQL 15), `pgbouncer`, `redis` en red aislada `travelhub_private`.
- **Integraciones:** Gotenberg (puerto 3000 para renderizado PDF headless) y Evolution API (puerto 8080).
- **Medios Persistentes:** Cloudflare R2 (`django-storages` + `boto3`).

### Pasos Mínimos para Entorno de Desarrollo Local

1. Clonar el repositorio y crear el entorno virtual:
   ```bash
   git clone <repo_url>
   cd travelhub_project
   python -m venv .venv
   .venv\Scripts\activate  # Windows PowerShell: .venv\Scripts\Activate.ps1
   ```
2. Instalar dependencias:
   ```bash
   pip install -r requirements/base.txt -r requirements/dev.txt
   ```
3. Configurar archivo de variables de entorno:
   ```bash
   cp .env.example .env.local
   # Modificar .env.local con las claves correspondientes
   ```
4. Ejecutar migraciones e inicializar base de datos:
   ```bash
   python manage.py migrate
   python manage.py createsuperuser
   ```
5. Iniciar servidor de desarrollo y workers:
   ```bash
   python manage.py runserver
   # En terminales separadas:
   celery -A travelhub worker -l info
   celery -A travelhub beat -l info
   ```

---

## 5. MAPA DE ARCHIVOS CRÍTICOS

```
travelhub_project/
├── travelhub/                             <- Configuración raíz de Django
│   ├── settings/
│   │   ├── base.py                        <- Configuración global, APPS, SAAS_PLAN_LIMITS (L540)
│   │   ├── production.py                  <- Security headers, SSL, Sentry, PgBouncer settings
│   │   ├── development.py                 <- Consola de email, Debug Toolbar
│   │   └── testing.py                     <- Overrides para pytest
│   ├── urls.py                            <- Router maestro de URLs (L58)
│   ├── urls_api.py                        <- Router DRF v1 (Bookings, CRM, Finance) (L11)
│   ├── celery.py                          <- Instanciación de app Celery
│   └── celery_beat_schedule.py            <- Programación periódica Crontab
│
├── core/                                  <- Núcleo del sistema SaaS, seguridad y multi-tenancy
│   ├── middleware/
│   │   ├── tenant.py                      <- ThreadLocalContextMiddleware (L165), ContextVars, agency_context
│   │   ├── domain.py                      <- MultiTenantDomainMiddleware (L10), resolución por subdominio
│   │   ├── rls.py                         <- rls_session_context (L10), SET LOCAL app.current_agencia_id
│   │   └── security_headers.py            <- SecurityHeadersMiddleware (L12), CSP dinámico con nonce
│   ├── middleware_saas.py                 <- SaaSLimitMiddleware, throttling por cuota de plan
│   ├── middleware_ai_ratelimit.py         <- Rate limiting específico para endpoints de IA
│   ├── security.py                        <- get_agencia_or_403, get_object_tenant_or_404 (L15), RBAC
│   ├── fields.py                          <- EncryptedCharField (L108), EncryptedTextField (Fernet)
│   ├── signals.py                         <- Listener post_save de boletos e ingesta
│   ├── db_router.py                       <- PrimaryReplicaRouter (separación lectura/escritura)
│   ├── tasks.py                           <- sync_bcv_rates, tareas periódicas del núcleo
│   └── models/
│       ├── base.py                        <- AgenciaManager (L48), AgenciaMixin (L197), SaasQuerySet (L15)
│       ├── agencia.py                     <- Agencia (L15), UsuarioAgencia (L374), AgenciaConfiguracion (L472)
│       ├── audit.py                       <- AuditLog (L16) con encadenamiento de hashes SHA-256
│       └── ai.py                          <- AIUsageLog (L6) para registro de costos de IA
│
└── apps/                                  <- Módulos de dominio de negocio
    ├── bookings/                          <- Emisión de boletos y gestión de ventas
    │   ├── models/
    │   │   ├── venta.py                   <- Venta, ItemVenta, PagoVenta, FeeVenta
    │   │   ├── importacion.py             <- BoletoImportado (estado_parseo, datos_parseados)
    │   │   └── servicios.py               <- Reservas de Hotel, Autos y Seguros
    │   ├── serializers.py                 <- Serializadores DRF
    │   ├── tasks.py                       <- retry_queued_boletos_task, procesar_boleto_async
    │   └── urls.py                        <- Router endpoints `/api/boletos/` y `/api/ventas/`
    │
    ├── automation/                        <- Parsers de GDS e Inteligencia Artificial
    │   ├── parsers/
    │   │   ├── ai_universal_parser.py     <- UniversalAIParser (L53), fallback heurístico + Gemini
    │   │   ├── kiu_parser.py              <- KiuParser (L15), parseo determinístico KIU
    │   │   ├── console_parser.py          <- ConsoleParser (L12), comandos de consola GDS
    │   │   ├── ticket_parser.py           <- FastDeterministicParsers (L18), extract_data_from_text (L306)
    │   │   ├── gemini_parser.py           <- GeminiParser (L14), parsing multimodal con imágenes/PDF
    │   │   └── adapter.py                 <- parse_ticket_with_new_parsers (L15), router de parsers GDS
    │   ├── services/
    │   │   ├── ai_engine.py               <- AIEngine (L90), llamada unificada a IA con resolución de keys
    │   │   ├── ai_router.py               <- GeminiRouter (L55), estructuración de PNR e itinerarios
    │   │   ├── ticket_parser_service.py   <- TicketParserService (L35), orquestador principal
    │   │   ├── ai_agent.py                <- Agente conversacional interactivo (Function Calling)
    │   │   └── ai_tools.py                <- Declaración de herramientas ejecutables por el AI Agent
    │   └── tasks.py                       <- process_web_uploaded_ticket, tareas Celery de automatización
    │
    ├── communications/                    <- Mensajería multicanal (WhatsApp y Telegram)
    │   ├── services/
    │   │   ├── telegram_unified.py        <- TelegramNotificationService, TelegramStorageService
    │   │   ├── notification_router.py     <- NotificationRouter (L73), enrutador WhatsApp/Telegram/Email
    │   │   └── file_storage_service.py    <- Almacenamiento de vouchers en Telegram/R2
    │   └── views/
    │       └── telegram_views.py          <- TelegramWebhookView, integración bidireccional Brain Assistant
    │
    ├── finance/                           <- Facturación SENIAT, cobranzas y Stripe
    │   ├── services/
    │   │   └── stripe_service.py          <- StripeService (L15), Checkout, Portal y Webhooks
    │   ├── views/
    │   │   └── views_webhooks.py          <- StripeWebhookView (L180), verificación de firma HMAC
    │   └── models/                        <- Factura, LiquidacionProveedor, Cobranza
    │
    ├── crm/                               <- Gestión de clientes, pasaportes y pipelines
    ├── contabilidad/                      <- Plan de cuentas y asientos contables automáticos
    ├── cms/                               <- Generación de contenido marketing e integración KB/RAG
    ├── cotizaciones/                      <- Presupuestos itinerantes para clientes
    └── reports/                           <- Generación de reportes PDF/Excel
```

---

## 6. LÓGICA DE MULTI-TENANCY

El aislamiento de datos en TravelHub se implementa mediante un esquema de **Defensa en Profundidad de 4 Capas**:

```
[ HTTP Request ]
       │
       ▼
 ┌──────────────────────────────────────────────────────────┐
 │ CAPA 1: MultiTenantDomainMiddleware (core/middleware/domain.py) │  -> Resuelve Agencia por subdominio/host
 └────────────────────────────┬─────────────────────────────┘
                              │
                              ▼
 ┌──────────────────────────────────────────────────────────┐
 │ CAPA 2: ThreadLocalContextMiddleware (core/middleware/tenant.py)│  -> Setea ContextVars & RLS en DB
 └────────────────────────────┬─────────────────────────────┘
                              │
                              ▼
 ┌──────────────────────────────────────────────────────────┐
 │ CAPA 3: AgenciaManager (core/models/base.py:48)          │  -> Auto-filtra Model.objects.all()
 └────────────────────────────┬─────────────────────────────┘
                              │
                              ▼
 ┌──────────────────────────────────────────────────────────┐
 │ CAPA 4: RLS PostgreSQL Policy (core/middleware/rls.py)    │  -> Restricción a nivel de motor DB
 └──────────────────────────────────────────────────────────┘
```

### Detalle de las 4 Capas de Aislamiento

#### Capa 1: Identificación del Tenant (`core/middleware/domain.py:10`)
`MultiTenantDomainMiddleware` examina el encabezado `Host` de la petición HTTP. Si coincide con un dominio personalizado o subdominio registrado en `Agencia`, inyecta la instancia en `request.agencia`. Si el dominio no existe, retorna error HTTP 404.

#### Capa 2: Contexto Thread/Task Safe & Seteo RLS (`core/middleware/tenant.py:165`)
`ThreadLocalContextMiddleware` vincula el usuario autenticado con su `UsuarioAgencia` y establece las variables contextuales asíncronas (`ContextVars`):
- `agency_var.set(agencia)`
- `user_var.set(user)`
- Ejecuta `rls_session_context(agencia.id)` (`core/middleware/rls.py:10`), el cual lanza en la sesión de base de datos PostgreSQL:
  ```sql
  SET LOCAL app.current_agencia_id = '<agencia_id>';
  SET LOCAL app.bypass_rls = 'false';
  ```
- Al finalizar el ciclo de la petición (bloque `finally`), resetea las variables a `'0'` para evitar contaminación entre peticiones en el pool de conexiones.

#### Capa 3: Filtro Automático en ORM (`core/models/base.py:48` y `L197`)
Todo modelo de negocio hereda de `AgenciaMixin`. Este mixin asigna como manager predeterminado `AgenciaManager`:

```python
# core/models/base.py
class AgenciaManager(models.Manager):
    def get_queryset(self):
        queryset = SaasQuerySet(self.model, using=self._db)
        if is_system_context():
            return queryset  # Bypass explícito para Celery
        agency = get_current_agency()
        if agency:
            return queryset.filter(agencia=agency)  # Filtro obligatorio por tenant
        user = get_current_user()
        if user and user.is_superuser:
            return queryset  # God Mode para superusuarios en /admin/
        return queryset.none()  # Fail-safe: si no hay contexto, no retorna registros
```

#### Capa 4: Row-Level Security en PostgreSQL (`core/middleware/rls.py:10`)
Las tablas con datos de agencias poseen políticas RLS aplicadas a nivel de PostgreSQL:
```sql
CREATE POLICY agencia_isolation_policy ON bookings_venta
    USING (agencia_id = NULLIF(current_setting('app.current_agencia_id', true), '')::integer
           OR current_setting('app.bypass_rls', true) = 'true');
```

### Ejecución de Tareas en Background (Celery)
Para tareas en segundo plano donde no existe petición HTTP activa, se utilizan los siguientes context managers:

1. **Contexto de Agencia Específica:**
   ```python
   from core.middleware import agency_context
   with agency_context(agencia_instance, reason="procesar_correo_ingresado"):
       # Model.objects.all() se filtra automáticamente para esa agencia
       Venta.objects.filter(...)
   ```

2. **Contexto de Sistema (Bypass de Multi-Tenancy):**
   ```python
   from core.middleware import system_context
   # Requiere ALLOW_SYSTEM_CONTEXT=1 en entorno
   with system_context(reason="sync_bcv_rates_cron", max_seconds=60.0):
       # Permite consultar y actualizar registros cross-tenant
       AgenciaConfiguracion.all_objects.filter(...)
   ```

---

## 7. ARQUITECTURA DE LA IA INTERNA

TravelHub integra inteligencia artificial mediante una arquitectura multicapa de parsers, motores conversacionales y herramientas con fallback automático:

```
                      [ Documento / Texto / PDF / EML ]
                                     │
                                     ▼
                      TicketParserService.procesar_boleto()
                                     │
         ┌───────────────────────────┴───────────────────────────┐
         │                                                       │
         ▼                                                       ▼
 ┌───────────────────────────────┐               ┌───────────────────────────────┐
 │ MOTOR 1: Parsers GDS          │               │ MOTOR 2: FastDeterministic    │
 │ (KiuParser, ConsoleParser)   │               │ (Regex Genericos)             │
 └──────────────┬────────────────┘               └───────────────┬───────────────┘
                │ (Si falla o falta confianza)                   │ (Si falla)
                └───────────────────────────┬────────────────────┘
                                            │
                                            ▼
                             ┌───────────────────────────────┐
                             │ MOTOR 3: UniversalAIParser    │
                             │ (Gemini 2.5 Flash / Vision)   │
                             └──────────────┬────────────────┘
                                            │
                                            ▼
                             ┌───────────────────────────────┐
                             │ ProviderChain (ai_engine.py)  │
                             │ Gemini -> OpenAI -> DeepSeek  │
                             └───────────────────────────────┘
```

### 7.1 Ticket Parser Pro & Service (`apps/automation/services/ticket_parser_service.py:35`)
Orquesta la extracción de datos desde boletos PDF, texto o correo electrónico:
1. **Detección y Caching:** Calcula un fingerprint SHA-256 del contenido. Si existe en Redis cache (TTL 24 horas), retorna el resultado parseado sin consumir CPU ni cuota de API.
2. **Parsers Deterministícos GDS:** Intenta extraer la información usando `parse_ticket_with_new_parsers()` (`apps/automation/parsers/adapter.py:15`), invocando `KiuParser` o `ConsoleParser`.
3. **Regex Generico (`FastDeterministicParsers`):** Si el GDS no es detectado, aplica expresiones regulares para capturar PNR, número de boleto (13 dígitos), pasajero e itinerarios.
4. **Parsing IA Fallback (`UniversalAIParser`):** Si el resultado determinístico es incompleto o de baja confianza, delega el texto o documento a `UniversalAIParser` (`apps/automation/parsers/ai_universal_parser.py:53`), usando `AIEngine`.

### 7.2 AI Engine & ProviderChain (`apps/automation/services/ai_engine.py:90`)
`AIEngine.call_gemini()` actúa como el cliente unificado para todas las solicitudes de IA del sistema:
- **Priorización de API Keys:**
  1. Clave privada de la agencia (`AgenciaConfiguracion.gemini_api_key`, desencriptada de `EncryptedCharField`).
  2. Clave global del sistema (`os.environ["GEMINI_API_KEY"]`).
- **Cadena de Fallback (ProviderChain):** Si Gemini falla por rate-limit (HTTP 429) o timeout, la solicitud conmuta automáticamente a OpenAI (`openai==2.48.0`) y posteriormente a DeepSeek via la interfaz compatible.
- **Modelos predeterminados:** `gemini-2.5-flash` para velocidad/eficiencia y `gemini-1.5-pro` para tareas complejas de razonamiento o parsing multimodal de alta densidad.

### 7.3 Agente Conversacional e Integración Brain Assistant (`apps/automation/services/ai_agent.py`)
El módulo de agente conversacional permite interactuar con el ERP en lenguaje natural mediante **Function Calling**:
- **Herramientas Ejecutables (`apps/automation/services/ai_tools.py`):** Define funciones que la IA puede invocar de forma segura, tales como buscar clientes, consultar estado de boletos, calcular totales de ventas o revisar la tasa BCV del día.
- **Canal Telegram Webhook (`apps/communications/views/telegram_views.py`):** Los mensajes entrantes al bot de Telegram son procesados por el webhook, resolviendo el contexto multi-tenant de la agencia correspondiente y respondiendo interactivamente mediante el agente de IA.

### 7.4 Registro de Uso y Rate Limiting
- **Auditoría de Costos (`core/models/ai.py:AIUsageLog`):** Registra cada llamada a la IA capturando agencia, modelo utilizado, tokens de entrada/salida, costo estimado en USD y funcionalidad ejecutada (`ticket_parsing`, `brain_assistant`, `marketing_copy`).
- **Control de Frecuencia (`core/middleware_ai_ratelimit.py`):** Limita el consumo de endpoints de IA (máximo 20 peticiones por minuto por IP/agencia y 200 peticiones diarias en planes básicos).

---

## 8. CONTRATO DE API / ENDPOINTS PRINCIPALES

### Autenticación y Sesión

| Método | Ruta | Propósito | Autenticación |
| :--- | :--- | :--- | :--- |
| **POST** | `/api/auth/jwt/obtain/` | Obtener par de tokens JWT (`access` y `refresh`). | Ninguna |
| **POST** | `/api/auth/jwt/logout/` | Invalidar token de refresco JWT. | JWT Token |
| **POST** | `/login/` | Iniciar sesión basada en cookies de sesión Django. | Ninguna |
| **GET** | `/auth/magic-request/` | Solicitar enlace mágico de inicio de sesión por email. | Ninguna |
| **GET** | `/auth/magic/<token>/` | Validar enlace mágico y autenticar usuario. | Ninguna |

### Core & ERP (Endpoints REST DRF `/api/`)

| Método | Ruta | Propósito | Roles / Permisos |
| :--- | :--- | :--- | :--- |
| **GET / POST** | `/api/boletos/` | Listar y registrar boletos importados. | Autenticado (Tenant) |
| **POST** | `/api/boletos/upload/` | Subir archivo PDF/TXT para parseo automático de boleto. | Autenticado (Tenant) |
| **POST** | `/api/boletos/<id>/retry-parse/` | Solicitar re-parseo de un boleto previamente fallido. | Autenticado (Tenant) |
| **GET / POST** | `/api/ventas/` | Listar y crear ventas consolidadas. | Autenticado (Tenant) |
| **GET / PUT** | `/api/ventas/<id>/` | Consultar o actualizar detalle de una venta. | Autenticado (Tenant) |
| **GET / POST** | `/api/facturas/` | Generar y listar facturas fiscales SENIAT. | Autenticado (Rol: Admin, Contador) |
| **GET / POST** | `/api/clientes/` | Gestión de clientes CRM y pasaportes. | Autenticado (Tenant) |
| **GET** | `/api/dashboard/stats/` | Obtener métricas y KPIs consolidados del dashboard. | Autenticado (Tenant) |
| **GET** | `/api/tasas-bcv/` | Consultar la tasa de cambio oficial BCV vigente. | Autenticado (Tenant) |
| **GET** | `/api/audit-logs/` | Consultar logs de auditoría forense del sistema. | Superusuario / Staff |

### Monitoreo & Sistema

| Método | Ruta | Propósito | Autenticación |
| :--- | :--- | :--- | :--- |
| **GET** | `/health/` | Healthcheck básico del servicio web y base de datos. | Ninguna |
| **GET** | `/health/metrics/` | Estado extendido de componentes (DB, Redis, Celery). | Ninguna |
| **GET** | `/prometheus/` | Exportador de métricas en formato Prometheus. | IP restringida / Staff |
| **POST** | `/csp-report/` | Endpoint receptor de violaciones de CSP. | Ninguna (Exento CSRF) |

### Webhooks Externos (Exentos de CSRF - Verificación de Firma Obligatoria)

| Método | Ruta | Propósito | Mecanismo de Seguridad |
| :--- | :--- | :--- | :--- |
| **POST** | `/system/webhooks/stripe/` | Procesar eventos de facturación y planes SaaS. | Firma HMAC en header `Stripe-Signature` (`views_webhooks.py:180`) |
| **POST** | `/system/webhooks/telegram/` | Recepción de mensajes del bot de Telegram. | Verificación de secreto en URL / Token del bot (`telegram_views.py`) |
| **POST** | `/system/webhooks/binance/` | Confirmaciones de pago Binance Pay. | Firma HMAC-SHA256 en header `X-Binance-Signature` |
| **POST** | `/system/webhooks/whatsapp/` | Notificaciones de recepción/entrega WhatsApp. | Token de verificación global de Evolution API |

---

## 9. SEGURIDAD Y REGLAS DE ORO

### Medidas de Seguridad Implementadas

#### 1. Cifrado en Reposo de Datos Sensibles (`core/fields.py:108`)
- `EncryptedCharField` y `EncryptedTextField` utilizan cifrado simétrico **Fernet** (AES-128-CBC + HMAC-SHA256).
- Los siguientes campos en `AgenciaConfiguracion` se almacenan siempre cifrados: `password_app_correo`, `telegram_bot_token`, `evolution_api_key`, `email_monitor_password`, `gemini_api_key`.
- Prevención de doble cifrado: si la cadena inicia con el prefijo Fernet `gAAAAA`, no se re-encripta.

#### 2. Protección Contra Ataques de Fuerza Bruta (`django-axes`)
Configurado en `travelhub/settings/base.py`:
- Bloqueo automático al superar 5 intentos fallidos de autenticación (`AXES_FAILURE_LIMIT = 5`).
- Cooldown de 1 hora (`AXES_COOLOFF_TIME = 1`).
- Seguimiento por combinación de nombre de usuario e dirección IP (`AXES_LOCKOUT_PARAMETERS = ["username", "ip_address"]`).

#### 3. Política de Tokens JWT Estricta
- Tokens de acceso con vida útil corta de 30 minutos (`ACCESS_TOKEN_LIFETIME = timedelta(minutes=30)`).
- Tokens de refresco con rotación y lista negra activa tras su uso (`ROTATE_REFRESH_TOKENS = True`, `BLACKLIST_AFTER_ROTATION = True`).

#### 4. Content Security Policy (CSP) Dinámico (`core/middleware/security_headers.py:12`)
- Inyección de un **nonce criptográfico aleatorio** de 16 bytes (`secrets.token_hex(16)`) generado por cada petición HTTP.
- Headers adicionales de seguridad forzados en cada respuesta: `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`, `X-Frame-Options: DENY`.

#### 5. Auditoría Forense Criptográfica (`core/models/audit.py:16`)
- Cada registro en `AuditLog` incluye una **cadena de hashes encadenados** (`previous_hash` y `record_hash` en SHA-256) al estilo de un libro contable inmutable.
- Permite detectar manipulaciones directas en la tabla de auditoría si la cadena de hashes se rompe.

---

### Reglas del Repositorio (Reglas de ORO)

> ⚠️ **IMPERATIVOS ARQUITECTÓNICOS ABSOLUTOS** — Ninguna IA ni desarrollador debe violar estas reglas bajo ninguna circunstancia.

```
[CRÍTICO] REGLA 1: NUNCA ejecutar Model.objects.get(pk=pk) sin filtrar por la agencia en vistas o APIs de usuario.
  - INCORRECTO: BoletoImportado.objects.get(pk=pk)
  - CORRECTO:   get_object_tenant_or_404(BoletoImportado, agencia, pk=pk)
  - CORRECTO:   BoletoImportado.objects.get(pk=pk, agencia=agencia)

[CRÍTICO] REGLA 2: NUNCA usar SQL dinámico o consultas crudas en texto (cursor.execute) para manipular datos de negocio.
  - Usar EXCLUSIVAMENTE Django ORM (objects.create(), objects.filter(), transaction.atomic()).

[CRÍTICO] REGLA 3: NUNCA importar librerías externas que no estén declaradas en requirements/base.txt.

[CRÍTICO] REGLA 4: NUNCA hardcodear API keys, tokens o contraseñas en código fuente.
  - Usar os.getenv() o campos EncryptedCharField en la base de datos.

[ALTO]    REGLA 5: Todo nuevo modelo de dominio de agencia DEBE heredar de AgenciaMixin (core.models.base).
  - Esto garantiza la auto-asignación de la agencia y el aislamiento automático por AgenciaManager.

[ALTO]    REGLA 6: En tareas Celery cross-tenant, envolver el bloque obligatoriamente en system_context(reason="...").
  - El parámetro 'reason' es obligatorio para trazabilidad en logs de auditoría.

[ALTO]    REGLA 7: Al activar USE_PGBOUNCER=True en entorno, se DEBE forzar CONN_MAX_AGE=0.
  - Mantener conexiones abiertas con PgBouncer en modo transacción provoca fugas de variables RLS entre requests.

[MEDIO]   REGLA 8: Las validaciones de negocio deben residir en los Modelos o Serializadores, NUNCA en los templates.

[MEDIO]   REGLA 9: Al extraer orígenes/destinos en regex para Sabre, usar clases de caracteres horizontales [\t ] y NO \s.
  - \s incluye saltos de línea (\n) y desplaza el offset de captura en patrones no codiciosos.

[MEDIO]   REGLA 10: El paquete core/ NUNCA debe importar módulos desde apps/*. La dependencia es unidireccional (apps/ -> core/).
```

---

## 10. BUGS Y LIMITACIONES CONOCIDAS

Deuda técnica registrada y gestionada (detalles completos en `TECH_DEBT_REMEDIATION.md`):

1. **Formatos No Estándar en Boletos Imprimibles Avior / Estelar:**
   - Ciertos boletos web generados como imagen dentro del PDF no contienen capa de texto ejecutable. Requieren procesamiento por Gemini Vision, lo que incrementa el tiempo de respuesta a 8-12 segundos.

2. **Parser GDS Amadeus:**
   - ✅ **RESUELTO:** Implementado `AmadeusParser` nativo (`apps/automation/parsers/amadeus_parser.py`) heredando de `BaseTicketParser` con soporte para boletos GDS Amadeus y recibos CheckMyTrip.

3. **Timeout en Extracción por Red Lenta:**
   - La tarea asíncrona de parseo tiene un `soft_time_limit` de 20 segundos. Si la API de Gemini responde con alta latencia, el estado del boleto pasa a `REVISION_REQUERIDA` para que un operador verifique manualmente.

---

## 11. BRECHAS EN REPARACIÓN (TRABAJO ACTIVO)

Estado actualizado de los ítems de remediación técnica y hardening en el repositorio:

| ID / Área | Descripción del Trabajo | Estado | Referencia de Verificación |
| :--- | :--- | :--- | :--- |
| **P0-002** | Vulnerabilidad IDOR en `BoletoRetryParseAPIView` | ✅ **Resuelto** | `get_object_tenant_or_404()` implementado en `apps/bookings/views/boleto_views.py:165` |
| **P0-003** | Vulnerabilidad IDOR en `VentaDoubleInvoiceAPIView` | ✅ **Resuelto** | `get_object_tenant_or_404()` implementado en `apps/bookings/views/boleto_views.py:365` |
| **P0-004** | Prevención de ejecución indefinida en `system_context()` | ✅ **Resuelto** | Control `max_seconds=60.0` y env var `ALLOW_SYSTEM_CONTEXT` en `core/middleware/tenant.py:67` |
| **P0-005** | Validación de firma HMAC en Webhook Stripe | ✅ **Resuelto** | `stripe.Webhook.construct_event()` en `apps/finance/views/views_webhooks.py:180` |
| **P0-006** | Prevención de fuga de información en tracebacks HTTP 500 | ✅ **Resuelto** | Patrón `error_id` opaco retornado al cliente y log estructurado en Sentry |
| **P1-001** | Eliminación de ejecuciones duplicadas por señales Django | ✅ **Resuelto** | Desduplicación de receivers `post_save` en `apps/bookings/signals.py` |
| **P1-003** | Incompatibilidad de `CONN_MAX_AGE` con PgBouncer | ✅ **Resuelto** | Sincronización automática de flag `USE_PGBOUNCER` en `travelhub/settings/base.py` |
| **P1-004** | Invalidación de cache de configuración de agencia | ✅ **Resuelto** | Inserción de signal de limpieza al actualizar `AgenciaConfiguracion` |
| **P1-007** | Sincronización asíncrona en notificaciones de WhatsApp | ✅ **Resuelto** | Despacho de notificaciones migrado a Celery `.delay()` |
| **P3-001** | Reintento automático de boletos encolados en error | ✅ **Resuelto** | Tarea programada `retry_queued_boletos_task` en `apps/bookings/tasks.py` |
| **Telegram** | Integración Brain Assistant bidireccional en Telegram | ✅ **Resuelto** | Webhook y enrutador activo en `apps/communications/views/telegram_views.py` |
| **Parser Amadeus** | Implementación de parser determinístico nativo Amadeus | ✅ **Resuelto** | `AmadeusParser` en `apps/automation/parsers/amadeus_parser.py` (100% tests pasados) |
| **P3-002** | Endpoint de polling para estado de parseo en tiempo real | ✅ **Resuelto** | `BoletoStatusAPIView` en `apps/bookings/views/boleto_status_api.py` (`/api/boletos/<pk>/status/`) |
| **P3-003** | Alerta cuota Gemini por agencia | ✅ **Resuelto** | `_check_daily_quota_alert()` en `apps/automation/services/ai_engine.py:428` |
| **P4-001** | Métricas de precisión del parser | ✅ **Resuelto** | `ParserMetricsCollector` en `apps/automation/metrics/parser_metrics.py` |
| **P4-003** | Versionado de datos_parseados | ✅ **Resuelto** | `_parser_version: "2.5.0"` y `_parsed_at` en `apps/automation/parsers/base_parser.py:186` |
| **P4-004** | Unificación definitiva de NotificationRouter multicanal | ✅ **Resuelto** | `NotificationRouter` en `apps/communications/services/notification_router.py` |

---

## APÉNDICE: PATRONES DE CÓDIGO RÁPIDOS PARA OTRA IA

### 1. Crear un Nuevo Endpoint REST Multi-tenant Seguro

```python
from rest_framework import viewsets
from core.security import get_agencia_from_request, get_object_tenant_or_404
from apps.bookings.models import Venta
from apps.bookings.serializers import VentaSerializer

class VentaViewSet(viewsets.ModelViewSet):
    serializer_class = VentaSerializer

    def get_queryset(self):
        # AgenciaManager auto-filtra por la agencia actual del usuario
        return Venta.objects.all()

    def get_object(self):
        agencia = get_agencia_from_request(self.request)
        return get_object_tenant_or_404(Venta, agencia, pk=self.kwargs["pk"])
```

### 2. Definir un Nuevo Modelo de Dominio de Agencia

```python
from django.db import models
from core.models.base import AgenciaMixin, SoftDeleteModel

class ServicioTuristico(AgenciaMixin, SoftDeleteModel):
    nombre = models.CharField(max_length=200)
    precio_usd = models.DecimalField(max_digits=12, decimal_places=2)

    # AgenciaMixin incluye automáticamente:
    # - ForeignKey('core.Agencia', on_delete=models.CASCADE)
    # - manager 'objects' (AgenciaManager) con filtrado multi-tenant
    # - manager 'all_objects' (Manager estándar para admin/sistema)

    class Meta:
        verbose_name = "Servicio Turístico"
        ordering = ["-id"]
```

### 3. Invocar la IA Interna con Fallback y Seguimiento de Costos

```python
from apps.automation.services.ai_engine import AIEngine

engine = AIEngine()
respuesta = engine.call_gemini(
    prompt="Resume el siguiente itinerario de vuelo...",
    feature="resumen_itinerario",  # Identificador para AIUsageLog
    temperature=0.2,
    agency=request.agencia,        # Resuelve API key de agencia o global
)

if "error" not in respuesta:
    contenido = respuesta.get("content")
```

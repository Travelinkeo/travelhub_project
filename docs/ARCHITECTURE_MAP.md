# TravelHub - Mapa de Arquitectura

> ERP SaaS Multi-tenant B2B para Agencias de Viajes

---

## 1. Visión General del Sistema

```mermaid
graph TB
    subgraph "CLIENTES"
        U["🧑 Usuarios<br/>(Agencias de Viaje)"]
        API["🔌 API Clients<br/>(JWT/REST)"]
        WEB["🌐 Web Browsers<br/>(HTMX + Alpine.js)"]
    end

    subgraph "INFRAESTRUCTURA"
        direction TB
        CF["☁️ Cloudflare Tunnel<br/>(HTTPS público)"]
        TF["🔄 Traefik<br/>(Reverse Proxy + SSL)"]
        NGINX["📁 Nginx<br/>(Static/Media files)"]
        WEBAPP["🐍 Django 5.2<br/>(Gunicorn 4w/2t)"]
        CELERY["⚡ Celery Worker<br/>(4 concurrentes)"]
        BEAT["⏰ Celery Beat<br/>(Tareas programadas)"]
    end

    subgraph "DATOS"
        PG["🗄️ PostgreSQL 16<br/>(Datos principales)"]
        REDIS["💨 Redis 7<br/>(Caché + Broker + Sesiones)"]
        R2["📦 Cloudflare R2<br/>(Archivos S3)"]
        GOTENBERG["📄 Gotenberg 8<br/>(HTML → PDF)"]
    end

    subgraph "EXTERNOS"
        STRIPE["💳 Stripe<br/>(Suscripciones SaaS)"]
        GEMINI["🤖 Google Gemini<br/>(IA: parsing, copilot)"]
        RESEND["📧 Resend<br/>(Email transaccional)"]
        EVOLUTION["💬 Evolution API<br/>(WhatsApp Business)"]
        TELEGRAM["📱 Telegram<br/>(Notificaciones Staff)"]
        SENTRY["🐛 Sentry<br/>(Monitor de errores)"]
        BCV["🏦 BCV<br/>(Tasas de cambio Vzla)"]
        BINANCE["₿ Binance Pay<br/>(Pagos cripto)"]
    end

    U --> CF
    API --> CF
    WEB --> CF
    CF --> TF
    TF --> WEBAPP
    TF --> NGINX
    WEBAPP --> PG
    WEBAPP --> REDIS
    WEBAPP --> R2
    WEBAPP --> GOTENBERG
    CELERY --> PG
    CELERY --> REDIS
    CELERY --> R2
    CELERY --> GOTENBERG
    BEAT --> REDIS
    WEBAPP --> STRIPE
    WEBAPP --> GEMINI
    WEBAPP --> RESEND
    WEBAPP --> EVOLUTION
    WEBAPP --> TELEGRAM
    WEBAPP --> SENTRY
    WEBAPP --> BCV
    WEBAPP --> BINANCE
    CELERY --> GEMINI
    CELERY --> RESEND
    CELERY --> EVOLUTION
    CELERY --> TELEGRAM

    style CF fill:#f96,stroke:#333
    style TF fill:#6cf,stroke:#333
    style PG fill:#4a4,stroke:#333,color:#fff
    style REDIS fill:#d44,stroke:#333,color:#fff
    style GEMINI fill:#a6f,stroke:#333
```

---

## 2. Arquitectura de Infraestructura (Docker Compose)

```mermaid
graph TB
    subgraph "Red: travelhub_public"
        TRAEFIK["Traefik v3.0<br/>:80, :443<br/>Let's Encrypt SSL"]
        WEB["web<br/>Django + Gunicorn<br/>:8000"]
        NGINX["nginx:1.25-alpine<br/>:8080<br/>Archivos estáticos"]
    end

    subgraph "Red: travelhub_private"
        DB["db<br/>PostgreSQL 16-alpine<br/>:5432<br/>shared_buffers=256MB"]
        CACHE["redis<br/>Redis 7-alpine<br/>:6379<br/>AOF persistence"]
        GOTENBERG["gotenberg<br/>Gotenberg 8<br/>:3000<br/>Chromium headless"]
        WORKER["celery_worker<br/>4 workers multi-cola<br/>ia_fast | ia_heavy | notifications"]
        SCHEDULER["celery_beat<br/>Programador<br/>Tareas periódicas"]
    end

    TRAEFIK --> WEB
    TRAEFIK --> NGINX
    WEB --> DB
    WEB --> CACHE
    WEB --> GOTENBERG
    WORKER --> DB
    WORKER --> CACHE
    WORKER --> GOTENBERG
    SCHEDULER --> CACHE

    style TRAEFIK fill:#6cf,stroke:#333
    style DB fill:#4a4,stroke:#333,color:#fff
    style CACHE fill:#d44,stroke:#333,color:#fff
```

### Tareas Programadas (Celery Beat)

| Frecuencia | Tarea |
|------------|-------|
| Cada 2 min | Procesar emails entrantes |
| Cada 15 min | Monitorear límites de deadline |
| Lun-Vie 9am/1pm | Sincronizar tasas BCV |
| Diario 9am | Revisar vencimiento pasaportes |
| Diario 10am | Revisar cumpleaños clientes |
| Diario 11am | Revisar pagos pendientes |
| Diario 3am | Backup de base de datos |

---

## 3. Arquitectura de Módulos (Aplicación Django)

```mermaid
graph TB
    subgraph "KERNEL — core"
        MT["🏢 Multi-Tenancy<br/>AgenciaManager + contextvars"]
        AUTH["🔐 Autenticación<br/>JWT / Magic Link / Session"]
        SEC["🛡️ Seguridad<br/>CSP / Fernet / AuditLog SHA-256"]
        BASE["📦 Base Models<br/>AgenciaMixin / SoftDelete"]
        MW["⚙️ Middleware<br/>Tenant / SaaS / RateLimit"]
        SIGNALS["📡 Signals<br/>Audit / Contabilidad / Passport"]
    end

    subgraph "DOMINIO — apps/"
        BOOKINGS["🎫 bookings<br/>Ventas / Itinerarios / Vouchers<br/>Tarifarios / GDS Parsing"]
        FINANCE["💰 finance<br/>Facturación / Liquidaciones<br/>Reconciliación / Retenciones"]
        CRM["👥 crm<br/>Clientes / Pasajeros<br/>Pasaportes / Oportunidades"]
        CONTAB["📊 contabilidad<br/>Plan Contable / Asientos<br/>Tasas BCV / Reportes"]
        COTIZ["📝 cotizaciones<br/>Pre-ventas / Cotizaciones<br/>PDF / WhatsApp sharing"]
        MARKETING["📣 marketing<br/>Campañas / Contenido<br/>IA imágenes"]
        CMS["📄 cms<br/>Artículos / Guías<br/>Redes Sociales"]
        COMMS["💬 communications<br/>WhatsApp / Telegram<br/>Email"]
        AUTO["🤖 automation<br/>Parsers IA (Gemini)<br/>20+ GDS adapters"]
    end

    subgraph "COMPARTIDO"
        COMMON["🗂️ common<br/>Catálogos: País, Ciudad, Aerolínea"]
        API["🔌 API REST<br/>drf-spectacular / OpenAPI 3.0<br/>Auto-generación ViewSets"]
    end

    MT --> BOOKINGS
    MT --> FINANCE
    MT --> CRM
    MT --> CONTAB
    MT --> COTIZ
    MT --> MARKETING
    MT --> CMS
    MT --> COMMS
    MT --> AUTO
    BOOKINGS --> COMMON
    BOOKINGS --> CRM
    BOOKINGS --> FINANCE
    FINANCE --> CONTAB
    FINANCE --> BOOKINGS
    COTIZ --> BOOKINGS
    COTIZ --> CRM
    AUTO --> BOOKINGS
    AUTO --> CRM
    AUTO --> GEMINI_AI["Google Gemini"]
    API --> BOOKINGS
    API --> FINANCE
    API --> CRM
    API --> CONTAB
    API --> COMMON

    style MT fill:#ff9,stroke:#333
    style AUTH fill:#ff9,stroke:#333
    style SEC fill:#ff9,stroke:#333
    style BOOKINGS fill:#9cf,stroke:#333
    style FINANCE fill:#9f9,stroke:#333
    style CRM fill:#f9f,stroke:#333
    style AUTO fill:#a6f,stroke:#333
```

### Responsabilidades por Módulo

| Módulo | Modelos Clave | Vistas Principales | Servicios |
|--------|---------------|--------------------|-----------|
| **bookings** | Venta, ItemVenta, Proveedor, TarifarioProveedor, BoletoImportado | Dashboard moderno, CRUD Ventas, Importar Boletos, Itinerarios, Hoteles | boleto_service, venta_service, voucher_service, revenue_auditor, pnr_parser |
| **finance** | Factura, FacturaConsolidada, LiquidacionProveedor, ConciliacionBoleto, LinkDePago | Facturación consolidada, Liquidaciones, Reconciliación, Tax Refund | Servicios de facturación, reconciliación y liquidación |
| **crm** | Cliente, Pasajero, PasaporteEscaneado, OportunidadViaje | Pipeline Kanban, Ficha cliente, Escaneo pasaporte | CRM bot, marketing automation |
| **contabilidad** | PlanContable, AsientoContable, DetalleAsiento, TasaCambioBCV | Libro diario, Balance, Estado de resultados | bcv_client, reportes |
| **cotizaciones** | Cotizacion, ItemCotizacion | Dashboard cotizaciones, Compartir WhatsApp | pdf_service |
| **automation** | (usa modelos de bookings/crm) | Endpoints de parsing | ticket_parser, gemini_parser, kiu_parser, 20+ parsers |

---

## 4. Modelo de Datos - Entidades Principales

```mermaid
erDiagram
    Agencia ||--o{ UsuarioAgencia : "tiene"
    Agencia ||--o{ Cliente : "posee"
    Agencia ||--o{ Proveedor : "gestiona"
    Agencia ||--o{ Venta : "registra"
    Agencia ||--o{ Factura : "emite"
    Agencia ||--o{ Cotizacion : "elabora"
    Agencia ||--o{ PlanContable : "define"
    Agencia ||--o{ AuditLog : "audita"

    Cliente ||--o{ Pasajero : "contiene"
    Cliente ||--o{ OportunidadViaje : "pipeline"
    Cliente ||--o{ Venta : "compra"

    Proveedor ||--o{ ProductoServicio : "ofrece"
    Proveedor ||--o{ TarifarioProveedor : "publica"
    Proveedor ||--o{ LiquidacionProveedor : "liquida"

    Venta ||--o{ ItemVenta : "detalla"
    Venta ||--o{ FeeVenta : "cobra fee"
    Venta ||--o{ PagoVenta : "recibe pago"
    Venta ||--o{ BoletoImportado : "importa"
    Venta ||--o{ FacturaConsolidada : "factura"

    ItemVenta ||--o{ AlojamientoReserva : "hotel"
    ItemVenta ||--o{ SegmentoVuelo : "vuelo"
    ItemVenta ||--o{ TrasladoServicio : "traslado"
    ItemVenta ||--o{ CruceroReserva : "crucero"
    ItemVenta ||--o{ AlquilerAutoReserva : "auto"

    Factura ||--o{ ItemFactura : "detalla"
    Factura ||--o{ ConciliacionBoleto : "concilia"

    LiquidacionProveedor ||--o{ ItemLiquidacion : "detalla"

    PlanContable ||--o{ AsientoContable : "agrupa"
    AsientoContable ||--o{ DetalleAsiento : "desglosa"

    Cotizacion ||--o{ ItemCotizacion : "detalla"

    Venta ||--o{ AuditLog : "registra"
    Cliente ||--o{ AuditLog : "registra"
    Proveedor ||--o{ AuditLog : "registra"
```

---

## 5. Flujo de Datos - Procesos Clave

### 5.1 Flujo de Importación de Boletos (GDS Parsing)

```mermaid
sequenceDiagram
    actor U as 👤 Usuario
    participant V as Views (upload)
    participant CT as Celery Task
    participant P as Parsers (automation)
    participant AI as 🤖 Gemini AI
    participant DB as PostgreSQL
    participant S as Signals (audit)

    U->>V: Sube PDF/EML del boleto
    V->>V: Validación MIME + tamaño
    V->>CT: Encola tarea async (ia_fast)
    V-->>U: Respuesta inmediata "Procesando..."

    CT->>P: text_extraction (PDF/EML → texto)
    P->>P: adapter (detecta GDS: Sabre/Amadeus/KIU/Copa)
    P->>AI: Envía texto estructurado
    AI-->>P: Datos parseados (JSON con schema)
    P->>P: normalization (estandariza nombres, fechas, montos)
    P->>DB: persistence → BoletoImportado
    P->>DB: venta_builder → Venta + ItemVenta + SegmentoVuelo
    S->>DB: AuditLog (acción: crear)
    S->>DB: AsientoContable (auto-contabilidad)
```

### 5.2 Flujo de Facturación y Liquidación

```mermaid
sequenceDiagram
    actor U as 👤 Usuario
    participant V as Finance Views
    participant SVC as Finance Services
    participant CT as Celery Task (ia_heavy)
    participant AI as 🤖 Gemini AI
    participant DB as PostgreSQL

    U->>V: Sube reporte del proveedor
    V->>CT: Encola reconciliación async
    CT->>SVC: Procesa datos del reporte
    CT->>DB: Busca Venta por localizador
    alt Match exacto
        SVC->>DB: Crea ConciliacionBoleto (match)
    else Sin match
        CT->>AI: Búsqueda difusa con Gemini
        AI-->>CT: Sugerencias de match
        SVC->>DB: Crea ConciliacionBoleto (pendiente revisión)
    end
    U->>V: Revisa y aprueba conciliaciones
    V->>DB: Genera LiquidacionProveedor
    V->>DB: Genera FacturaConsolidada (VEN-NIF)
```

### 5.3 Flujo Multi-Tenant (Aislamiento de Datos)

```mermaid
sequenceDiagram
    participant R as HTTP Request
    participant MW1 as DomainMiddleware
    participant MW2 as ThreadLocalMiddleware
    participant V as View + SaaSMixin
    participant M as AgenciaManager
    participant DB as PostgreSQL

    R->>MW1: Resuelve tenant por subdominio
    MW1->>MW2: Setea agency_id en contextvars
    MW2->>V: Request con contexto de agencia
    V->>M: get_queryset()
    M->>DB: SELECT ... WHERE agencia_id = [tenant]
    Note over M,DB: Filtro automático en cada query
    DB-->>V: Solo datos del tenant
    V-->>R: Respuesta aislada
```

---

## 6. Stack Tecnológico

```mermaid
graph LR
    subgraph "Backend"
        DJ["Django 5.2"]
        DRF["DRF 3.15"]
        CEL["Celery 5.5"]
    end
    subgraph "Base de Datos"
        PG["PostgreSQL 16"]
        R["Redis 7"]
    end
    subgraph "Frontend SSR"
        DT["Django Templates"]
        TW["TailwindCSS"]
        HTMX["HTMX"]
        ALP["Alpine.js"]
    end
    subgraph "IA / Automatización"
        GEM["Google Gemini"]
        GCP["Google Cloud AI"]
    end
    subgraph "Comunicaciones"
        EVO["Evolution API (WhatsApp)"]
        TG["Telegram Bot"]
        RS["Resend (Email)"]
    end
    subgraph "Pagos / Facturación"
        ST["Stripe"]
        BN["Binance Pay"]
    end
    subgraph "Infra / DevOps"
        DK["Docker Compose"]
        TF["Traefik v3"]
        GH["GitHub Actions"]
        SN["Sentry"]
        CF["Cloudflare R2/Tunnel"]
    end

    DJ --> DRF
    DJ --> CEL
    DJ --> PG
    DJ --> R
    DJ --> GEM
    DJ --> EVO
    DJ --> ST
    DT --> TW
    DT --> HTMX
    DT --> ALP

    style DJ fill:#2b5,stroke:#333,color:#fff
    style PG fill:#4a4,stroke:#333,color:#fff
    style TW fill:#38b,stroke:#333,color:#fff
    style GEM fill:#a6f,stroke:#333
```

---

## 7. Estrategia de Seguridad

| Capa | Mecanismo | Implementación |
|------|-----------|----------------|
| **Autenticación** | JWT + Magic Link + Session | `simplejwt`, `core/models/magic_link.py` |
| **Anti fuerza bruta** | django-axes | 5 intentos max, 1h cooldown |
| **Autorización** | RBAC (admin/manager/vendor) | `SaaSMixin` en cada View |
| **Aislamiento tenant** | contextvars + ORM filter | `AgenciaManager`, `ThreadLocalContextMiddleware` |
| **Defensa en profundidad** | PostgreSQL RLS | Políticas por agencia_id |
| **Encriptación en reposo** | Fernet (AES-128-CBC) | `EncryptedCharField` para PII |
| **Auditoría inmutable** | Cadena criptográfica SHA-256 | `AuditLog` con `previous_hash` |
| **CSP + XSS** | Nonces rotativos + bleach sanitizer | `SecurityHeadersMiddleware` |
| **Rate Limiting** | Por IP, por tenant, por endpoint | DRF throttling + middleware |
| **Validación SSRF** | Proxy validation | `evolution_proxy_views.py` |
| **Webhooks idempotentes** | Idempotency keys | Stripe + Binance webhooks |
| **TOCTOU race prevention** | `select_for_update()` | Campos `localizador`, `numero_factura` |

---

## 8. Integraciones Externas

```mermaid
graph LR
    TH["TravelHub"]
    TH -->|"Suscripciones + Pagos"| Stripe["💳 Stripe"]
    TH -->|"Parsing IA + Copilot + Reconciliación"| Gemini["🤖 Google Gemini"]
    TH -->|"Email transaccional"| Resend["📧 Resend SMTP"]
    TH -->|"WhatsApp Business"| Evolution["💬 Evolution API<br/>(self-hosted)"]
    TH -->|"Notificaciones Staff"| Telegram["📱 Telegram Bot"]
    TH -->|"Document OCR"| DocAI["🔍 Google Cloud<br/>Document AI"]
    TH -->|"Almacenamiento"| R2["📦 Cloudflare R2<br/>(S3-compatible)"]
    TH -->|"Túnel HTTPS"| Tunnel["☁️ Cloudflare Tunnel"]
    TH -->|"Monitoreo errores"| Sentry["🐛 Sentry"]
    TH -->|"Tasas BCV"| BCV["🏦 Banco Central<br/>de Venezuela"]
    TH -->|"Pagos cripto"| Binance["₿ Binance Pay"]
    TH -->|"Imágenes marketing"| Unsplash["🖼️ Unsplash"]
    TH -->|"GDS (vuelos/hoteles)"| Amadeus["✈️ Amadeus API"]
    TH -->|"PDF generation"| Gotenberg["📄 Gotenberg<br/>(Chromium headless)"]
```

---

## 9. Flujo SaaS (Self-Service Onboarding)

```mermaid
sequenceDiagram
    actor C as 🏢 Nueva Agencia
    participant LP as Landing Page
    participant ST as Stripe Checkout
    participant WH as Stripe Webhook
    participant DB as PostgreSQL
    participant EM as Resend Email

    C->>LP: Selecciona plan (Starter/Pro/Enterprise)
    LP->>ST: Redirige a Stripe Checkout
    ST-->>C: Pago completado
    ST->>WH: POST webhook (checkout.session.completed)
    WH->>WH: Verifica firma HMAC
    WH->>DB: Crea Agencia + suscripción
    WH->>DB: Activa feature flags del plan
    WH->>EM: Envía Magic Link de bienvenida
    EM-->>C: Email con link de acceso
    C->>LP: Click en Magic Link → Dashboard
```

---

## 10. Estructura de Directorios Simplificada

```
travelhub/
├── settings.py                 # 850 líneas - Configuración central
├── urls.py                     # Router maestro de URLs
├── celery.py                   # App Celery + routing de colas
│
├── core/                       # 🏗️ KERNEL Multi-tenant
│   ├── models/                 # Agencia, AuditLog, MagicLink, AI, FeatureFlags
│   ├── views/                  # 58 archivos de vistas (dashboard, auth, billing, etc.)
│   ├── api/                    # API hotel + mixins
│   ├── services/               # Parsers, reports, agency_cache
│   ├── templates/              # 28 subdirectorios (base, dashboard, crm, finance, etc.)
│   ├── middleware*.py          # Tenant, SaaS, AI rate limit, performance, security
│   ├── serializers.py          # 869 líneas - Todos los serializers DRF
│   ├── signals*.py             # Audit, contabilidad, passport
│   └── security.py             # get_user_active_agency, IDOR protection
│
├── apps/                       # 📦 MÓDULOS DE DOMINIO
│   ├── bookings/               # 🎫 Ventas, itinerarios, vouchers, GDS
│   │   ├── models/             # Venta, ItemVenta, Proveedor, Tarifario, Boletos
│   │   ├── views/              # Dashboard, ventas, boletos, itinerarios, hoteles
│   │   ├── services/           # boleto, venta, voucher, revenue_auditor, pnr_parser
│   │   ├── urls.py             # 173 líneas - Todas las rutas
│   │   └── tasks.py            # Tareas Celery de bookings
│   │
│   ├── finance/                # 💰 Facturación, liquidaciones, conciliación
│   │   ├── models/             # Factura, FacturaConsolidada, Liquidacion, Reconciliacion
│   │   ├── views/              # Invoices, settlements, tax refund
│   │   ├── services/           # Lógica financiera
│   │   └── tasks_*.py          # Tasks: reconciliation, settlements, fiscal, tax_refund
│   │
│   ├── crm/                    # 👥 Clientes, pasajeros, oportunidades
│   ├── contabilidad/           # 📊 Plan contable, asientos, tasas BCV
│   ├── cotizaciones/           # 📝 Pre-ventas y cotizaciones
│   ├── automation/             # 🤖 20+ parsers GDS, AI engine
│   │   ├── parsers/            # ticket_parser, gemini_parser, kiu_parser, adapter, etc.
│   │   └── ai/                 # AI schemas
│   ├── marketing/              # 📣 Campañas, contenido IA
│   ├── cms/                    # 📄 Artículos, guías de destino
│   ├── communications/         # 💬 WhatsApp, Telegram, Email
│   └── common/                 # 🗂️ Catálogos compartidos
│
├── docs/                       # 📚 44 archivos de documentación
├── tests/                      # 🧪 97 archivos de tests (77%+ coverage)
├── docker/                     # 🐳 Configs Evolution API instances
├── nginx/                      # 🌐 Config Nginx
├── traefik_data/               # 🔄 Config Traefik reverse proxy
├── requirements/               # 📋 base.txt + prod.txt
├── scripts/                    # 🔧 Scripts utilitarios
├── .github/workflows/          # ⚙️ CI/CD (test, lint, security, docker)
│
├── Dockerfile                  # Python 3.13-slim
├── docker-compose.yml          # 7 servicios
├── docker-compose.prod.yml     # Producción
├── Makefile                    # Build automation
├── manage.py                   # Django management
└── conftest.py                 # Pytest config
```

---

## Resumen de Complejidad

| Métrica | Valor |
|---------|-------|
| **Apps Django** | 10 (core + 9 domain) |
| **Archivos de vistas** | 58+ en core, más por módulo |
| **Modelos** | 60+ modelos de datos |
| **Serializers DRF** | 869 líneas en core, más por módulo |
| **Parsers GDS** | 20+ adapters (Sabre, Amadeus, KIU, Copa, etc.) |
| **Tareas Celery** | 15+ archivos de tasks |
| **Tests** | 97 archivos, 77%+ coverage |
| **Servicios Docker** | 7 (traefik, db, redis, web, nginx, gotenberg, celery) |
| **Integraciones externas** | 12 APIs/servicios |
| **Documentación** | 44 archivos en docs/ |
| **Colas Celery** | 4 (default, ia_fast, ia_heavy, notifications) |
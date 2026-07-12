# TRAVELHUB — DOCUMENTACIÓN MAESTRA PARA IA

> **Propósito:** Esta documentación está diseñada para que cualquier IA (incluyendo asistentes de código) pueda entender la arquitectura completa del proyecto, localizar archivos rápidamente, y hacer cambios sin romper nada.
>
> **Proyecto:** TravelHub — Plataforma SaaS Multi-Tenant ERP/CRM para Agencias de Viajes
> **Stack:** Django 5.2 + Python 3.13 + PostgreSQL 16 + Redis 7 + Celery 5.5
> **Ubicación:** `C:\Users\ARMANDO\travelhub_project`

---

## 📦 TABLA DE CONTENIDOS

1. [Estructura General del Proyecto](#1-estructura-general-del-proyecto)
2. [Stack Tecnológico Detallado](#2-stack-tecnológico-detallado)
3. [Arquitectura Multi-Tenant (SaaS)](#3-arquitectura-multi-tenant-saas)
4. [Módulos / Apps de Django](#4-módulos--apps-de-django)
5. [Modelos de Base de Datos (Diagrama Lógico)](#5-modelos-de-base-de-datos)
6. [URLs y Routing](#6-urls-y-routing)
7. [Sistema de Parseo de Boletos (Core del Negocio)](#7-sistema-de-parseo-de-boletos)
8. [Tareas Asíncronas (Celery)](#8-tareas-asíncronas-celery)
9. [Sistema de Señales (Signals)](#9-sistema-de-señales-signals)
10. [Seguridad y Middleware](#10-seguridad-y-middleware)
11. [Integraciones Externas](#11-integraciones-externas)
12. [Frontend y Templates](#12-frontend-y-templates)
13. [Pruebas (Tests)](#13-pruebas-tests)
14. [Despliegue (Docker)](#14-despliegue-docker)
15. [Guía Rápida para IA: Cómo Hacer Cambios](#15-guía-rápida-para-ia-cómo-hacer-cambios)

---

## 1. ESTRUCTURA GENERAL DEL PROYECTO

```
travelhub_project/
├── travelhub/                 # ⚙️ Configuración central de Django
│   ├── settings.py            #    Settings con toda la configuración
│   ├── urls.py                #    URLConf raíz (router maestro)
│   ├── wsgi.py / asgi.py      #    Entry points WSGI/ASGI
│   ├── celery.py              #    Configuración de Celery app + task routing
│   └── celery_beat_schedule.py#    Programación de tareas periódicas
│
├── core/                      # 🧠 Núcleo del sistema (SaaS, Auth, Utilidades)
│   ├── models/                #    Modelos compartidos (Agencia, AuditLog, AI, etc.)
│   │   ├── agencia.py         #      Agencia, UsuarioAgencia, AgenciaBranding, AgenciaConfiguracion
│   │   ├── audit.py           #      AuditLog (con encadenamiento SHA-256)
│   │   ├── ai.py              #      AIUsageLog (tracking de consumo IA)
│   │   ├── base.py            #      AgenciaMixin, SoftDeleteModel, AgenciaManager
│   │   ├── feature_flags.py   #      FeatureFlag
│   │   ├── magic_link.py      #      MagicLinkToken
│   │   ├── historial_boletos.py #    AnulacionBoleto, HistorialCambioBoleto
│   │   ├── cron_api_key.py    #      CronApiKey
│   │   └── migration_checks.py#      MigrationCheck
#   ├── middleware.py           #    ThreadLocalContextMiddleware, MultiTenantDomainMiddleware
#   ├── middleware_saas.py      #    SaaSLimitMiddleware (enforcement de cuotas)
#   ├── middleware_ai_ratelimit.py#  AIRateLimitMiddleware
#   ├── middleware_performance.py#   Middleware de performance profiling
#   ├── managers.py             #    TenantManager (manager legacy)
#   ├── mixins.py               #    SaaSMixin, AgencyRoleRequiredMixin, HtmxResponseMixin
#   ├── permissions.py          #    IsStaffOrGroupWrite, rol_requerido
#   ├── fields.py               #    EncryptedCharField, EncryptedTextField (Fernet)
#   ├── security.py             #    Funciones de seguridad (get_user_active_agency, etc.)
#   ├── validators.py           #    Validadores compartidos
#   ├── throttling.py           #    Throttle personalizado
#   ├── signals.py              #    Señales principales del sistema
#   ├── signals_audit.py        #    Señales de auditoría automáticas
#   ├── signals_bypass.py       #    Mecanismo de bypass de señales
#   ├── signals_contabilidad.py #    Señales de contabilidad
#   ├── signals_passport.py     #    Señales de pasaportes
#   ├── tasks.py                #    Tareas Celery principales (>1000 líneas)
#   ├── storage.py              #    Configuración de almacenamiento R2
#   ├── cache.py / cache_utils.py #  Utilidades de cache
#   ├── api/                    #    APIs REST (hotel_api, mixins tenant)
#   ├── api_registry.py         #    Registro automático de APIs
#   ├── chatbot/                #    Módulo de chatbot con IA
#   ├── context_processors.py   #    Context processors (agency_context, csp_nonce)
#   ├── dashboard_stats.py      #    Estadísticas para dashboard
#   ├── parsers/                #    (legacy) — parsers antiguos
#   ├── views/                  #    Vistas del core
#   │   ├── auth_views.py       #      JWT, Magic Link
#   │   ├── onboarding_views.py #      Onboarding SaaS
#   │   ├── voucher_views.py    #      Generación de vouchers PDF
#   │   ├── flights_views.py    #      Búsqueda de vuelos
#   │   ├── hotel_views.py      #      Búsqueda/detalle de hoteles
#   │   ├── god_mode_views.py   #      Panel SuperAdmin
#   │   ├── agencia_views.py    #      Configuración de agencia
#   │   ├── cron_views.py       #      Endpoints para cron jobs externos
#   │   ├── erp_views.py        #      Vistas ERP legacy
#   │   ├── upload.py           #      Vistas de subida de boletos
#   │   ├── boleto_api_views.py #      API de boletos
#   │   ├── analytics/          #      Dashboards analíticos
#   │   ├── reportes_views.py   #      Reportes contables
#   │   ├── search_views.py     #      Búsqueda global
#   │   ├── settings_views.py   #      Configuración de branding
#   │   ├── translator_views.py #      Traductor
#   │   ├── intelligence_views.py#     GDS Analyzer
#   │   ├── wiki_views.py       #      Wiki GDS
#   │   ├── webhooks_views.py   #      Webhooks entrantes
#   │   ├── migration_api.py    #      API de migración
#   │   ├── fix_user_view.py    #      Utilidad de fix de usuarios
#   │   ├── evolution_qr_view.py#      QR WhatsApp Evolution
#   │   ├── notifications.py    #      Vistas de notificaciones
#   │   └── health_views.py     #      Health check
#   ├── management/commands/    #    Comandos manage.py personalizados
#   ├── templatetags/           #    Template tags personalizados
#   ├── templates/              #    Templates compartidos
#   └── tests/                  #    Tests del core
#
# ├── apps/                     # 📦 Módulos de negocio (Django Apps)
# │   ├── common/               #    Catálogos compartidos (País, Ciudad, Aerolínea)
# │   ├── bookings/             #    Módulo principal de reservas y ventas
# │   ├── finance/              #    Facturación VEN-NIF, pagos, conciliación
# │   ├── crm/                  #    Clientes, pasajeros, oportunidades Kanban
# │   ├── contabilidad/         #    Plan de cuentas, asientos, tasas BCV
# │   ├── cotizaciones/         #    Cotizaciones con IA
# │   ├── marketing/            #    Campañas, activos, generación de contenido
# │   ├── cms/                  #    CMS de contenido (artículos, guías)
# │   ├── communications/       #    Notificaciones, email, WhatsApp
# │   ├── automation/           #    Parseo de boletos (GDS), automatización
# │   └── accounting_assistant/ #    Asistente contable IA
# │
# ├── docs/                     # 📚 Documentación
# ├── static/                   # 🎨 Archivos estáticos (CSS, JS, imágenes)
# ├── templates/                # 🖌️ Templates Django (raíz)
# ├── fixtures/                 # 📋 Datos de prueba (JSON)
# ├── tests/                    # 🧪 Tests globales
# ├── scripts/                  # 📜 Scripts de utilidad
# ├── batch_scripts/            # 📜 Scripts batch Windows
# ├── requirements/             # 📦 Dependencias Python
# │   ├── base.txt             #    Dependencias base (Django, DRF, Celery, etc.)
# │   ├── prod.txt             #    Dependencias de producción
# │   └── local.txt            #    Dependencias de desarrollo
# │
# ├── docker-compose.yml        # 🐳 Orquestación Docker
# ├── docker-compose.dev.yml    #    Docker desarrollo
# ├── docker-compose.test.yml   #    Docker testing
# ├── Dockerfile                #    Imagen Docker
# ├── nginx.conf / nginx/       #    Configuración Nginx
# ├── traefik_data/             #    Configuración Traefik (SSL)
# ├── Makefile                  #    Comandos make (test, lint, format, etc.)
# ├── manage.py                 #    Entry point de Django
# ├── conftest.py               #    Configuración raíz de pytest
# ├── pytest.ini                #    Configuración de pytest
# ├── mypy.ini                  #    Configuración de type checking
# ├── .coveragerc / .ruff.toml #    Configuración de coverage y linting
# ├── .env                      #    Variables de entorno (LOCAL)
# └── .env.production           #    Variables de entorno (PRODUCCIÓN)
```

---

## 2. STACK TECNOLÓGICO DETALLADO

### Backend
| Tecnología | Versión | Propósito |
|-----------|---------|-----------|
| Django | 5.2.14 | Framework web principal |
| Django REST Framework | 3.15.2 | APIs REST |
| Python | 3.13 | Lenguaje de programación |
| Celery | 5.5.3 | Tareas asíncronas |
| Redis | 7 | Broker de Celery + Caché + Sesiones |
| PostgreSQL | 16 | Base de datos principal |
| Gunicorn | - | Servidor WSGI de producción |

### Frontend
| Tecnología | Propósito |
|-----------|-----------|
| Django Templates | SSR (Server-Side Rendering) |
| TailwindCSS | Framework CSS utilitario |
| HTMX | Interactividad sin JavaScript pesado |
| Alpine.js | Interactividad ligera en componentes |
| Unfold | Tema moderno para Django Admin |

### IA y Parsing
| Tecnología | Propósito |
|-----------|-----------|
| Google Gemini (genai) | Motor de IA principal (parseo, copywriting, chatbot) |
| google-cloud-aiplatform | Vertex AI (Document AI para OCR) |
| PyMuPDF (fitz) | Extracción de texto de PDFs |
| pytesseract | OCR para imágenes de boletos |

### Infraestructura
| Tecnología | Propósito |
|-----------|-----------|
| Docker / Docker Compose | Contenedores y orquestación |
| Cloudflare Tunnel | Exposición segura a Internet |
| Traefik | Proxy inverso + SSL (Let's Encrypt) |
| Cloudflare R2 | Almacenamiento de archivos (S3-compatible) |
| Sentry | Monitoreo de errores |
| GitHub Actions | CI/CD |

### Integraciones
| Servicio | Propósito |
|---------|-----------|
| Stripe | Facturación SaaS (suscripciones) |
| Resend | Envío de correos electrónicos |
| Evolution API | WhatsApp Business |
| Telegram Bot | Notificaciones y almacenamiento |
| Amadeus API | GDS (búsqueda de vuelos) |
| Unsplash API | Imágenes para marketing |
| Gotenberg | Generación de PDFs (HTML → PDF) |

---

## 3. ARQUITECTURA MULTI-TENANT (SaaS)

### 3.1 Concepto
TravelHub es una plataforma **multi-tenant** donde cada agencia de viajes tiene sus datos aislados. Hay 4 planes: `FREE`, `BASIC`, `PRO`, `ENTERPRISE` (definidos en `settings.py:SAAS_PLAN_LIMITS`).

### 3.2 Mecanismo de Aislamiento

#### 3.2.1 `AgenciaMixin` (`core/models/base.py:96`)
- Clase abstracta que TODOS los modelos de negocio heredan.
- Añade automáticamente un campo `agencia = ForeignKey('core.Agencia')`.
- El manager `AgenciaManager` filtra automáticamente por la agencia del contexto actual.

#### 3.2.2 `AgenciaManager` (`core/models/base.py:32`)
- Filtra querysets por `agencia` del contexto actual.
- Soporta soft delete (filtra `is_deleted=False`).
- Permite bypass para superusuarios y comandos de gestión.
- Usa `SaasQuerySet` para forzar agencia en `bulk_create` y `update`.

#### 3.2.3 `ThreadLocalContextMiddleware` (`core/middleware.py`)
- Almacena el contexto actual (usuario, agencia, IP) en `ContextVar` (thread-safe).
- Extrae la agencia del subdominio (`MultiTenantDomainMiddleware`).
- Soporta **God Mode** (superusuarios impersonando agencias).
- Las funciones de acceso: `get_current_agency()`, `get_current_user()`, `get_current_request_meta()`, `is_impersonating()`.

#### 3.2.4 `SaaSMixin` (`core/mixins.py:11`)
- Mixin para **vistas basadas en clase**.
- Filtra querysets por agencia del usuario actual.
- Aplica RBAC por rol (`admin`, `gerente`, `vendedor`, `contador`, `operador`, `consulta`).
- Los vendedores solo ven sus propios registros en modelos operacionales.

#### 3.2.5 `SaaSLimitMiddleware` (`core/middleware_saas.py`)
- Intercepta requests POST/PUT/PATCH.
- Verifica cuotas según el plan (`SAAS_PLAN_LIMITS`).
- Bloquea con 403 si se excede el límite.
- Cachea el conteo de uso en Redis.

### 3.3 Planes SaaS
```python
SAAS_PLAN_LIMITS = {
    'FREE':  { 'users': 1, 'storage_mb': 100,  'leads_per_month': 20,  'sales_per_month': 20  },
    'BASIC': { 'users': 2, 'storage_mb': 500,  'leads_per_month': 50,  'sales_per_month': 50  },
    'PRO':   { 'users': 10,'storage_mb': 5000, 'leads_per_month': 500, 'sales_per_month': 500 },
    'ENTERPRISE': { 'users': 999, 'storage_mb': 99999, 'leads_per_month': 99999, 'sales_per_month': 99999 },
}
```

### 3.4 Modelo `Agencia` (`core/models/agencia.py`)
- **`Agencia`**: Perfil de la agencia. Campos: nombre, RIF, IATA, contacto, dirección, redes sociales.
- **`AgenciaBranding`**: Logos (claro/oscuro/base64/PDF), colores (6 variantes), temas UI (obsidian, swiss, cyber, nordic, midnight, sunset), plantillas (boletos/vouchers/facturas).
- **`AgenciaConfiguracion`**: Moneda, zona horaria, plan SaaS, Stripe IDs, credenciales encriptadas (Telegram, email, WhatsApp, Gemini API key), configuración fiscal venezolana.
- **`UsuarioAgencia`**: Relación User ↔ Agencia con roles.

---

## 4. MÓDULOS / APPS DE DJANGO

### 4.1 `core` — Núcleo del Sistema
**Ubicación:** `core/`
**Propósito:** Configuración central, autenticación, multi-tenancy, auditoría, seguridad, modelos base.

**Archivos clave:**
- `core/models/agencia.py` — Modelos de agencia, branding, configuración
- `core/models/audit.py` — AuditLog con encadenamiento SHA-256
- `core/models/base.py` — AgenciaMixin, SoftDeleteModel, AgenciaManager
- `core/middleware.py` — Contexto thread-local, multi-tenancy por dominio
- `core/middleware_saas.py` — Enforcement de cuotas SaaS
- `core/mixins.py` — SaaSMixin, AgencyRoleRequiredMixin
- `core/tasks.py` — Tareas Celery (procesamiento de correos, parseo, etc.)
- `core/fields.py` — Campos encriptados (EncryptedCharField, EncryptedTextField)
- `core/signals.py` — Señales centrales (post-save de boletos, pagos, facturas)
- `core/urls_system.py` — URLs del sistema (god-mode, wiki, settings, etc.)
- `core/views/god_mode_views.py` — Panel de SuperAdmin
- `core/views/auth_views.py` — JWT, Magic Links
- `core/views/onboarding_views.py` — Onboarding de nuevas agencias

### 4.2 `apps.bookings` — Ventas y Reservas
**Ubicación:** `apps/bookings/`
**Propósito:** Gestión completa de ventas, reservas, boletos aéreos, hoteles, traslados, etc.

**Modelos (`apps/bookings/models/`):**
- `venta.py` → **`Venta`**: Modelo maestro de ventas. Multi-tenant. Estados: pendiente pago → pagada parcial → pagada total → confirmada → en viaje → completada/cancelada. Campos: cliente, pasajeros, localizador, moneda, subtotal, impuestos, total, pagos, fees. Soporta soft delete.
- `venta.py` → **`ItemVenta`**: Items individuales de una venta (boletos, hoteles, servicios).
- `venta.py` → **`VentaAuditFinding`**: Hallazgos de auditoría de revenue leak.
- `venta.py` → **`VentaParseMetadata`**: Metadatos de parseo asociados a ventas.
- `importacion.py` → **`BoletoImportado`**: Boleto aéreo importado (PDF/image). Campos: archivo, texto extraído, JSON parseado, estado (pendiente/parseado/error), GDS detectado, venta asociada.
- `importacion.py` → **`SolicitudAnulacion`**: Solicitud de anulación de boleto.
- `importacion.py` → **`BoletoImportadoTransito`**: Boleto en tránsito (procesamiento parcial).
- `pagos.py` → **`FeeVenta`**: Comisiones/cargos adicionales.
- `pagos.py` → **`PagoVenta`**: Pagos recibidos (monto, método, fecha, confirmado).
- `servicios.py` → **`Proveedor`**: Proveedores (aerolíneas, consolidadores, DMCs).
- `servicios.py` → **`ProductoServicio`**: Catálogo de productos/servicios.
- `servicios.py` → **`ComisionProveedorServicio`**: Comisiones por proveedor/servicio.
- `servicios.py` → **`ProductoTerrestre`**: Productos terrestres (traslados, excursiones).
- `componentes.py` → **`AlojamientoReserva`**, **`TrasladoServicio`**, **`ActividadServicio`**, **`SegmentoVuelo`**, **`AlquilerAutoReserva`**, **`EventoServicio`**, **`CircuitoTuristico`**, **`CircuitoDia`**, **`PaqueteAereo`**, **`CruceroReserva`**, **`ServicioAdicionalDetalle`**: Componentes de viaje.
- `tarifario.py` → **`TarifarioProveedor`**, **`HotelTarifario`**, **`TipoHabitacion`**, **`TarifaHabitacion`**, **`Amenity`**, **`ImagenHotel`**: Tarifarios hoteleros.

**Vistas clave (`apps/bookings/bookings_views.py`):**
- `VentaListView`, `VentaCreateView`, `VentaDetailView`, `VentaUpdateView`, `VentaDeleteView`
- `dashboard_main`, `dashboard_stats_htmx`, `RevenueLeakDashboardView`

**URLs (`apps/bookings/urls.py`):**
- `/ventas/` — CRUD de ventas
- `/proveedores/` — CRUD de proveedores
- `/dashboard/` — Dashboard principal
- `/cotizaciones/` — Cotizaciones
- `/hoteles/` — Búsqueda de hoteles
- `/flights/` — Búsqueda de vuelos
- `/api/` — REST API (ViewSets automáticos)
- `/v/<uuid:token>/` — Vistas públicas (itinerarios, vouchers)

### 4.3 `apps.finance` — Finanzas
**Ubicación:** `apps/finance/`
**Propósito:** Facturación VEN-NIF, pagos, conciliación, retenciones, tasas de cambio.

**Modelos (`apps/finance/models/`):**
- `core_finance.py` → **`Factura`** (alias `FacturaConsolidada`): Factura con normativa venezolana. Campos: emisor RIF/razón social, cliente identificación, montos en USD/BS, IVA 16%/8%, IGTF 3%, retenciones ISLR, exportación de servicios.
- `core_finance.py` → **`ItemFactura`**: Líneas de factura.
- `core_finance.py` → **`GastoOperativo`**: Gastos operativos.
- `core_finance.py` → **`TransaccionPago`**: Transacciones de pago.
- `core_finance.py` → **`PagoBinance`**: Pagos vía Binance.
- `core_finance.py` → **`DocumentoExportacion`**: Documentos de exportación.
- `core_finance.py` → **`PropuestaTransaccionIA`**: Propuestas generadas por IA.
- `currencies.py` → **`Moneda`**: Catálogo de monedas.
- `currencies.py` → **`TasaCambio`**, **`TipoCambio`**: Tasas de cambio.
- `reconciliacion.py` → **`ConciliacionBoleto`**, **`ReporteReconciliacion`**, **`LineaReporteReconciliacion`**: Conciliación de boletos.
- `retenciones.py` → **`RetencionISLR`**: Retenciones de ISLR.
- `checkout.py` → **`LinkDePago`**: Links de pago.
- `comisiones.py` → **`ComisionVenta`**, **`LiquidacionAgente`**, **`ReglaComision`**: Comisiones.
- `recaudacion.py` → **`CanalRecaudacion`**, **`Pago`**: Canales de recaudación.
- `facturas_proveedores.py` → **`FacturaProveedor`**: Facturas de proveedores.
- `tax_refund.py` → **`TaxRefundOpportunity`**: Oportunidades de devolución de impuestos.
- `fiscal.py` → Modelos fiscales (imprenta digital, libros fiscales).

**Tareas Celery:** `tasks.py`, `tasks_fiscal.py`, `tasks_notifications.py`, `tasks_reconciliation.py`, `tasks_settlements.py`, `tasks_tax_refund.py`

### 4.4 `apps.crm` — CRM
**Ubicación:** `apps/crm/`
**Propósito:** Gestión de clientes, pasajeros, oportunidades Kanban, pasaportes.

**Modelos (`apps/crm/models.py`):**
- **`Cliente`**: Cliente (pagador). Campos: nombres, apellidos, tipo (natural/jurídico), identificación (V/E/J/P/G), dirección, contactos, nacionalidad, ciudad, notas, historial. Multi-tenant.
- **`Pasajero`**: Pasajero (viajero). Campos: nombres, pasaporte, fecha vencimiento pasaporte, foto. Puede ser el mismo que el cliente.
- **`OportunidadViaje`**: Oportunidad Kanban (etapas: lead → calificado → cotizando → negociando → cerrado ganado/perdido).
- **`MensajeWhatsApp`**: Mensajes de WhatsApp almacenados.
- **`PasaporteEscaneado`**: Pasaportes escaneados (OCR).
- **`ComisionFreelancer`**: Comisiones para freelancers.

**Vistas:** `clientes_views.py`, `pasajeros_views.py`, `kanban_views.py`, `ai_chat_views.py`, `ocr_views.py`, `inbox_views.py`, `marketing_views.py`, `webhook_views.py`, `freelancer_views.py`, `actions_views.py`

### 4.5 `apps.contabilidad` — Contabilidad
**Ubicación:** `apps/contabilidad/`
**Propósito:** Plan de cuentas, asientos contables, tasas BCV.

**Modelos (`apps/contabilidad/models.py`):**
- **`PlanContable`**: Plan de cuentas contable. Campos: código, nombre, tipo (activo/pasivo/patrimonio/ingreso/gasto), nivel, cuenta padre.
- **`AsientoContable`**: Asiento contable. Campos: número, fecha, descripción, tipo (diario/compras/ventas/nómina/apertura/cierre/ajuste), estado (borrador/contabilizado/anulado), totales debe/haber.
- **`DetalleAsiento`**: Líneas de asiento. Campos: cuenta contable, debe, haber, descripción.
- **`TasaCambioBCV`**: Tasas de cambio oficiales del BCV (Venezuela).

**Archivos clave:** `services.py` (servicios contables), `bcv_client.py` (cliente BCV), `tasas_venezuela_client.py`, `reportes.py` (reportes contables).

### 4.6 `apps.cotizaciones` — Cotizaciones
**Ubicación:** `apps/cotizaciones/`
**Propósito:** Cotizaciones con asistencia de IA.

**Modelos (`apps/cotizaciones/models.py`):**
- **`Cotizacion`**: Cotización. Campos: cliente, pasajeros, items, totales, estados (borrador/enviada/aprobada/rechazada/convertida).
- **`ItemCotizacion`**: Items de cotización.

**Archivos clave:** `views.py` (MagicQuoter), `pdf_service.py` (PDF de cotizaciones), `ai_schemas.py` (esquemas Gemini).

### 4.7 `apps.marketing` — Marketing
**Ubicación:** `apps/marketing/`
**Propósito:** Campañas, activos, generación de contenido con IA.

**Modelos (`apps/marketing/models.py`):**
- **`Campania`**: Campaña de marketing.
- **`ActivoMarketing`**: Activos (imágenes, videos, textos).
- **`ConfiguracionMarketing`**: Configuración de marketing (preferencias IA, redes sociales).

**Servicios:** `flyer_service.py`, `promotion_service.py`, `copywriter_service.py`, `flash_marketing_service.py`, `forecast_service.py`

### 4.8 `apps.cms` — CMS
**Ubicación:** `apps/cms/`
**Propósito:** Contenido (artículos, guías de destino, posts redes sociales).

**Modelos (`apps/cms/models.py`):**
- **`Articulo`**: Artículo de blog.
- **`GuiaDestino`**: Guía turística de destinos.
- **`PostRedesSociales`**: Posts para redes sociales.

### 4.9 `apps.communications` — Comunicaciones
**Ubicación:** `apps/communications/`
**Propósito:** Notificaciones multicanal (WhatsApp, Telegram, Email).

**Archivos clave:**
- `services/email_monitor_service.py` — Monitor IMAP para recibir boletos por email
- `services/notification_dispatcher.py` — Despachador de notificaciones
- `notifications/` — Implementaciones de canales de notificación
- `models/` — Modelos de comunicación

### 4.10 `apps.automation` — Automatización y Parseo
**Ubicación:** `apps/automation/`
**Propósito:** Parseo inteligente de boletos aéreos multi-GDS con IA.

**Archivos clave (`apps/automation/parsers/`):**
- `base_parser.py` — Clase base para parsers
- `kiu_parser.py` — Parser específico KIU
- `gemini_parser.py` — Parser universal con Gemini AI
- `ai_universal_parser.py` — Parser universal basado en IA
- `ticket_parser.py` — Parser principal de tickets
- `text_extraction.py` — Extracción de texto de PDFs/imágenes
- `normalization.py` — Normalización de datos extraídos
- `extraction.py` — Extracción de campos específicos
- `persistence.py` — Persistencia de datos parseados
- `venta_builder.py` — Construcción de ventas desde datos parseados
- `registry.py` — Registro de parsers por tipo de GDS
- `adapter.py` — Adaptador de parsers legacy
- `console_parser.py` — Parser de consola para debugging
- `tarifario_parser.py` — Parser de tarifarios hoteleros
- `supplier_report_parser.py` — Parser de reportes de proveedores
- `web_receipt_parser.py` — Parser de recibos web
- `airline_utils.py` — Utilidades de aerolíneas
- `parsing_utils.py` — Utilidades de parseo
- `pdf_generation.py` — Generación de PDFs post-parseo

### 4.11 `apps.common` — Comunes
**Ubicación:** `apps/common/`
**Propósito:** Catálogos y utilidades compartidas.

**Modelos (`apps/common/models.py`):**
- **`Pais`**: Catálogo de países (ISO 2, ISO 3, nombre).
- **`Ciudad`**: Catálogo de ciudades (nombre, código IATA, país, región/estado).
- **`Aerolinea`**: Catálogo de aerolíneas (código IATA, ICAO, nombre, RIF, activa).

**Servicios:** `services/saas_quota_service.py`, `utils/celery_utils.py`

### 4.12 `apps.accounting_assistant` — Asistente Contable IA
**Ubicación:** `apps/accounting_assistant/`

---

## 5. MODELOS DE BASE DE DATOS

### 5.1 Diagrama de Relaciones Principales

```
core.Agencia (1) ── (N) core.UsuarioAgencia ── (N) auth.User
    │
    ├── (1) core.AgenciaBranding (logo, colores, temas)
    ├── (1) core.AgenciaConfiguracion (plan, Stripe, credenciales)
    │
    ├── (N) bookings.Venta (ventas de la agencia)
    │       ├── (N) bookings.ItemVenta (items de cada venta)
    │       ├── (N) bookings.PagoVenta (pagos)
    │       ├── (N) bookings.FeeVenta (comisiones/cargos)
    │       ├── (N) bookings.BoletoImportado (boletos importados)
    │       ├── (N) bookings.AlojamientoReserva (hoteles)
    │       ├── (N) bookings.TrasladoServicio (traslados)
    │       ├── (N) bookings.ActividadServicio (actividades)
    │       ├── (N) bookings.SegmentoVuelo (segmentos de vuelo)
    │       ├── (N) bookings.AlquilerAutoReserva (autos)
    │       ├── (N) bookings.CircuitoTuristico (circuitos)
    │       ├── (N) bookings.PaqueteAereo (paquetes)
    │       ├── (N) bookings.CruceroReserva (cruceros)
    │       ├── (N) bookings.ServicioAdicionalDetalle (adicionales)
    │       └── (N) finance.Factura (facturas asociadas)
    │
    ├── (N) crm.Cliente (clientes)
    │       ├── (N) crm.Pasajero (pasajeros)
    │       └── (N) crm.OportunidadViaje (oportunidades Kanban)
    │
    ├── (N) contabilidad.AsientoContable (asientos contables)
    │       └── (N) contabilidad.DetalleAsiento (detalles)
    │
    ├── (N) contabilidad.PlanContable (cuentas contables)
    ├── (N) cotizaciones.Cotizacion (cotizaciones)
    ├── (N) marketing.Campania (campañas)
    ├── (N) finance.GastoOperativo (gastos)
    ├── (N) finance.RetencionISLR (retenciones)
    └── (N) core.AuditLog (logs de auditoría)
```

### 5.2 Modelos Core (Compartidos)

#### `Agencia` (`core/models/agencia.py:14`)
| Campo | Tipo | Descripción |
|-------|------|-------------|
| id | AutoField (PK) | ID de la agencia |
| nombre | CharField(200, unique) | Nombre de la agencia |
| nombre_comercial | CharField(200) | Nombre comercial |
| rif | CharField(20) | RIF venezolano |
| iata | CharField(20) | Código IATA |
| activa | BooleanField | Si la agencia está activa |
| dominio_personalizado | CharField(255, unique, null) | Dominio personalizado |
| branding | OneToOneField(AgenciaBranding) | Branding asociado |
| configuracion | OneToOneField(AgenciaConfiguracion) | Configuración asociada |
| propietario | ForeignKey(User) | Usuario propietario |

#### `AuditLog` (`core/models/audit.py:18`)
| Campo | Tipo | Descripción |
|-------|------|-------------|
| id_audit_log | AutoField (PK) | ID |
| modelo | CharField(120) | Nombre del modelo |
| object_id | CharField(120) | ID del objeto |
| venta | ForeignKey(Venta, nullable) | Venta asociada |
| agencia | ForeignKey(Agencia, nullable) | Agencia |
| user | ForeignKey(User, nullable) | Usuario que hizo el cambio |
| accion | CharField(10) | CREATE/UPDATE/DELETE/STATE/LOGIN/LOGOUT |
| descripcion | TextField | Descripción del cambio |
| datos_previos | JSONField | Datos antes del cambio |
| datos_nuevos | JSONField | Datos después del cambio |
| metadata_extra | JSONField | IP, User-Agent, impersonación |
| creado | DateTimeField | Fecha de creación |
| previous_hash | CharField(64) | Hash del registro anterior |
| record_hash | CharField(64, unique) | SHA-256 del registro actual |

### 5.3 Modelos de Bookings

#### `Venta` (`apps/bookings/models/venta.py:21`)
| Campo | Tipo | Descripción |
|-------|------|-------------|
| id_venta | AutoField (PK) | ID |
| uuid | UUIDField | Token público |
| localizador | CharField(20) | Código PNR/localizador |
| cliente | ForeignKey(Cliente) | Cliente pagador |
| creado_por | ForeignKey(User) | Usuario creador |
| pasajeros | ManyToManyField(Pasajero) | Pasajeros del viaje |
| cotizacion_origen | OneToOneField(Cotizacion, null) | Cotización origen |
| moneda | ForeignKey(Moneda) | Moneda de la venta |
| tasa_cambio_bcv | DecimalField | Tasa BCV al momento |
| subtotal | DecimalField | Subtotal |
| impuestos | DecimalField | Impuestos |
| total_venta | DecimalField | Total (editable=False) |
| monto_pagado | DecimalField | Monto pagado |
| saldo_pendiente | DecimalField | Saldo pendiente (editable=False) |
| estado | CharField(3) | PEN/PAR/PAG/CNF/VIA/COM/FAL/CAN |
| tipo_venta | CharField(4) | B2C/B2B/MICE/PKG/CIR/TLD/SEG/OTR |
| canal_origen | CharField(3) | ADM/IMP/API/WEB/MIG/OTR |
| agencia | ForeignKey(Agencia) | (heredado de AgenciaMixin) |
| created_at / updated_at | DateTimeField | Timestamps |
| is_deleted | BooleanField | Soft delete (heredado) |

#### `BoletoImportado` (`apps/bookings/models/importacion.py`)
| Campo | Tipo | Descripción |
|-------|------|-------------|
| id_boleto | AutoField (PK) | ID |
| archivo | FileField | Archivo PDF/imagen |
| texto_extraido | TextField | Texto extraído del PDF |
| json_parseado | JSONField | Datos estructurados parseados |
| gds_detectado | CharField(20) | KIU/SABRE/AMADEUS/COPA/WINGO/TK_CONNECT/UNKNOWN |
| estado | CharField(20) | PENDIENTE/PROCESANDO/PARSEADO/ERROR/DUPLICADO |
| error_mensaje | TextField | Mensaje de error si falló |
| venta_asociada | ForeignKey(Venta, null) | Venta creada a partir del boleto |
| agencia | ForeignKey(Agencia) | Agencia propietaria |
| fecha_creacion | DateTimeField | Fecha de subida |

#### `ItemVenta` (`apps/bookings/models/venta.py`)
| Campo | Tipo | Descripción |
|-------|------|-------------|
| id_item | AutoField (PK) | ID |
| venta | ForeignKey(Venta) | Venta padre |
| producto_servicio | ForeignKey(ProductoServicio) | Tipo de servicio |
| proveedor | ForeignKey(Proveedor, null) | Proveedor |
| descripcion | TextField | Descripción del item |
| cantidad | IntegerField | Cantidad |
| precio_unitario | DecimalField | Precio unitario |
| total | DecimalField | Total del item |
| comision | DecimalField | Comisión |
| agencia | ForeignKey(Agencia) | Agencia |

### 5.4 Modelos de Finance

#### `Factura` (`apps/finance/models/facturacion.py:22`)
| Campo | Tipo | Descripción |
|-------|------|-------------|
| id_factura | AutoField (PK) | ID |
| numero_factura | CharField(50, unique) | Número de factura |
| numero_control | CharField(50) | Número de control fiscal |
| venta_asociada | ForeignKey(Venta, null) | Venta asociada |
| agencia | ForeignKey(Agencia, null) | Agencia emisora |
| cliente | ForeignKey(Cliente, null) | Cliente |
| moneda | ForeignKey(Moneda) | Moneda |
| emisor_rif / emisor_razon_social / emisor_direccion_fiscal | | Datos del emisor |
| cliente_identificacion | CharField(50) | RIF/Cédula/Pasaporte del cliente |
| base_imponible / monto_iva / monto_igtf / total / total_bs | DecimalField | Montos |
| exportacion_servicios | BooleanField | Si es exportación (IVA 0%) |
| fecha_emision / fecha_vencimiento | DateField | Fechas |

### 5.5 Modelos de Contabilidad

#### `AsientoContable` (`apps/contabilidad/models.py:18`)
| Campo | Tipo | Descripción |
|-------|------|-------------|
| id_asiento | AutoField (PK) | ID |
| numero_asiento | CharField(20, unique) | Número de asiento |
| fecha_contable | DateField | Fecha contable |
| descripcion_general | CharField(255) | Descripción |
| tipo_asiento | CharField(3) | DIA/COM/VEN/NOM/APE/CIE/AJU |
| estado | CharField(3) | BOR/CON/ANU |
| total_debe / total_haber | DecimalField | Totales (editable=False) |
| moneda | ForeignKey(Moneda) | Moneda |
| agencia | ForeignKey(Agencia) | Agencia |

### 5.6 Modelos de CRM

#### `Cliente` (`apps/crm/models.py`)
| Campo | Tipo | Descripción |
|-------|------|-------------|
| id_cliente | AutoField (PK) | ID |
| tipo_cliente | CharField(10) | NATURAL / JURIDICO |
| tipo_identificacion | CharField(2) | V/E/J/P/G |
| identificacion | CharField(20) | Número de ID |
| primer_nombre / segundo_nombre / primer_apellido / segundo_apellido | CharField | Nombres |
| razon_social | CharField(200) | Razón social (si jurídico) |
| email / telefono_movil / telefono_fijo | | Contacto |
| direccion / ciudad / pais / nacionalidad | | Dirección |
| agencia | ForeignKey(Agencia) | Agencia |

---

## 6. URLS Y ROUTING

### 6.1 Router Maestro (`travelhub/urls.py`)

```
/                              → RedirectView → bookings:modern_dashboard
/dashboard/                    → RedirectView → bookings:modern_dashboard
/admin/                        → Django Admin (Unfold themed)
/accounts/                     → django.contrib.auth.urls
/login/                        → auth_views.LoginView
/logout/                       → auth_views.LogoutView
/api/auth/jwt/obtain/          → TokenObtainPairView (JWT login)
/api/auth/jwt/logout/          → TokenLogoutView
/auth/magic-request/           → MagicLinkRequestView
/auth/magic/<token>/           → MagicLinkVerifyView
/onboarding/                   → SaaSOnboardingView
/onboarding/agency/            → OnboardingAgencyView

# Módulos (include de apps)
/bookings/                     → apps.bookings.urls (CRUD ventas, dashboard, hoteles, vuelos)
/finance/                      → apps.finance.urls (facturación, pagos, conciliación)
/crm/                          → apps.crm.urls (clientes, pasajeros, kanban, OCR)
/system/                       → core.urls_system (god-mode, wiki, settings, tools)
/accounting/                   → apps.contabilidad.urls (asientos, plan de cuentas, tasas)
/cms/                          → apps.cms.urls (artículos, guías)
/marketing/                    → apps.marketing.urls (campañas, activos, hub)
/cotizaciones/                 → apps.cotizaciones.urls (cotizaciones, magic quoter)

# Documentación API
/api/schema/                   → SpectacularAPIView (OpenAPI schema)
/api/docs/                     → SpectacularSwaggerView (Swagger UI)
/api/redoc/                    → SpectacularRedocView (ReDoc)
```

### 6.2 URLs de Bookings (`apps/bookings/urls.py`)

```
/ventas/                       → VentaListView
/ventas/nueva/                 → VentaCreateView
/ventas/<pk>/                  → VentaDetailView
/ventas/<pk>/editar/           → VentaUpdateView
/ventas/<pk>/eliminar/         → VentaDeleteView
/ventas/<pk>/timeline/         → VentaTimelineView
/ventas/<venta_pk>/items/agregar/ → ItemVentaCreateView (HTMX)
/ventas/items/<pk>/editar/     → ItemVentaUpdateView (HTMX)
/ventas/<venta_pk>/fees/agregar/ → FeeVentaCreateView (HTMX)
/ventas/<venta_pk>/pagos/agregar/ → PagoVentaCreateView (HTMX)

/proveedores/                  → ProveedorListView
/proveedores/nuevo/            → ProveedorCreateView
/proveedores/<pk>/editar/      → ProveedorUpdateView
/proveedores/<pk>/eliminar/    → ProveedorDeleteView

/dashboard/                    → dashboard_main + dashboard_stats_htmx
/dashboard/modern/             → DashboardView (moderno)
/dashboard/whatsapp-qr/        → whatsapp_qr_view
/dashboard/whatsapp-pairing/   → whatsapp_pairing_code_view

/hoteles/                      → HotelListView (búsqueda)
/hoteles/<slug>/               → HotelDetailView
/flights/                      → FlightSearchView
/marketing/hub/                → MarketingHubView
/auditoria/                    → RevenueLeakDashboardView

/cotizaciones/                 → CotizacionDashboardView
/cotizaciones/magic/           → MagicQuoterView
/cotizaciones/nueva/           → CotizacionCreateView

/v/<uuid:token>/               → PublicItineraryView (white-label)
/v/<uuid:token>/pdf/           → PublicVoucherPDFView
/v/hotel/<id>/pdf/             → PublicHotelVoucherPDFView

/api/productoservicio/         → ProductoServicioViewSet (REST)
/api/cotizaciones/             → CotizacionViewSet (REST)
/api/v1/gds/ingest-pnr/       → api_ingest_pnr_view
```

### 6.3 URLs del Sistema (`core/urls_system.py`)

```
/system/god-mode/              → GodModeDashboardView
/system/intelligence/gds-analyzer/ → GDSAnalyzerView
/system/agencia/configuracion/ → AgenciaSettingsView
/system/agencia/usuarios/      → AgenciaUsersListView
/system/agencia/auditoria/     → AgenciaAuditLogListView
/system/settings/branding/     → BrandingSettingsView
/system/wiki/gds/              → wiki_gds_list
/system/api/cron/...           → Cron job endpoints
/system/tools/traductor/       → TraductorView
/system/api/docs/              → Swagger/ReDoc (duplicado)
```

---

## 7. SISTEMA DE PARSEO DE BOLETOS

### 7.1 Flujo General

```
1. ENTRADA: PDF o imagen de boleto aéreo (email upload, web upload, API)
       │
2. EXTRACCIÓN: apps/automation/parsers/text_extraction.py
   - PyMuPDF para PDFs
   - pytesseract OCR para imágenes
       │
3. DETECCIÓN GDS: apps/automation/parsers/extraction.py
   - Identifica el GDS (KIU, SABRE, AMADEUS, COPA, WINGO, TK_CONNECT)
   - Basado en patrones del texto
       │
4. PARSEO: apps/automation/parsers/
   ├── kiu_parser.py          → Regex para KIU
   ├── gemini_parser.py       → Gemini AI universal
   ├── ai_universal_parser.py → IA para casos complejos
   └── ticket_parser.py       → Coordinador de parsers
       │
5. NORMALIZACIÓN: apps/automation/parsers/normalization.py
   - Estandariza campos (fechas, montos, códigos)
       │
6. PERSISTENCIA: apps/automation/parsers/persistence.py
   - Guarda JSON parseado en BoletoImportado.json_parseado
       │
7. CONSTRUCCIÓN: apps/automation/parsers/venta_builder.py
   - Crea Venta + ItemVenta + FeeVenta + PagoVenta automáticamente
```

### 7.2 Archivos Clave

| Archivo | Propósito |
|---------|-----------|
| `apps/automation/parsers/base_parser.py` | Clase abstracta base para todos los parsers |
| `apps/automation/parsers/registry.py` | Registro central de parsers por GDS |
| `apps/automation/parsers/ticket_parser.py` | Orquestador principal del parseo |
| `apps/automation/parsers/text_extraction.py` | Extracción de texto de PDFs/imágenes |
| `apps/automation/parsers/extraction.py` | Detección de campos específicos |
| `apps/automation/parsers/normalization.py` | Normalización y limpieza de datos |
| `apps/automation/parsers/gemini_parser.py` | Parser usando Google Gemini |
| `apps/automation/parsers/kiu_parser.py` | Parser específico para GDS KIU |
| `apps/automation/parsers/ai_universal_parser.py` | Parser universal basado en IA |
| `apps/automation/parsers/adapter.py` | Adaptador para parsers legacy |
| `apps/automation/parsers/venta_builder.py` | Construcción automática de ventas |
| `apps/automation/parsers/persistence.py` | Persistencia de datos parseados |
| `apps/automation/parsers/supplier_report_parser.py` | Parseo de reportes de proveedores |
| `apps/automation/parsers/tarifario_parser.py` | Parseo de tarifarios hoteleros |
| `apps/automation/parsers/web_receipt_parser.py` | Parseo de recibos web |
| `apps/automation/parsers/airline_utils.py` | Utilidades específicas de aerolíneas |
| `apps/automation/parsers/parsing_utils.py` | Utilidades generales de parseo |
| `apps/automation/parsers/pdf_generation.py` | Generación de PDF desde datos parseados |

### 7.3 Modelos Involucrados

- **`BoletoImportado`**: Almacena el archivo original, texto extraído, JSON parseado.
- **`BoletoImportadoTransito`**: Estado intermedio durante el procesamiento.
- **`Venta`**: Venta creada a partir del boleto parseado.
- **`ItemVenta`**: Items creados automáticamente.
- **`SegmentoVuelo`**: Segmentos de vuelo extraídos.
- **`FeeVenta`**: Comisiones/cargos detectados.
- **`PagoVenta`**: Pagos detectados.

---

## 8. TAREAS ASÍNCRONAS (CELERY)

### 8.1 Configuración de Colas (`travelhub/celery.py`)

| Cola | Propósito | Prioridad |
|------|-----------|-----------|
| `default` | Tareas normales (parseo, OCR) | Normal |
| `ia_fast` | Tareas IA que el usuario espera (<5s) | Alta |
| `ia_heavy` | Tareas IA masivas (>1min) | Baja |
| `notifications` | WhatsApp y correos | Normal |

### 8.2 Tareas Programadas (Celery Beat)

**En `travelhub/celery.py` (principal):**
| Tarea | Schedule | Descripción |
|-------|----------|-------------|
| `apps.automation.tasks.master_mail_ingestion_cron` | Cada 5 min | Ingesta de correos multi-tenant |
| `apps.bookings.tasks.monitorear_tiempos_limite_periodico_task` | Cada 15 min | Monitoreo de tiempos límite |

**En `travelhub/celery_beat_schedule.py` (secundario):**
| Tarea | Schedule | Descripción |
|-------|----------|-------------|
| `core.tasks.process_incoming_emails` | Cada 2 min | Procesamiento de correos entrantes |
| `core.tasks.check_passport_expiry` | 9:00 AM diario | Verificar vencimiento de pasaportes |
| `core.tasks.check_client_birthdays` | 10:00 AM diario | Verificar cumpleaños de clientes |
| `core.tasks.check_pending_payments` | 11:00 AM diario | Recordatorios de pagos pendientes |
| `core.tasks.sync_bcv_rates` | 9AM/1PM (lun-vie) | Sincronizar tasas BCV |
| `core.tasks.backup_database_task` | 3:00 AM diario | Backup de base de datos |

### 8.3 Tareas Principales (`core/tasks.py`)

| Tarea | Propósito |
|-------|-----------|
| `process_incoming_emails` | Orquestador: revisa correos de todas las agencias activas |
| `parsear_boleto_individual` | Parseo individual de un boleto (subido manualmente) |
| `procesar_pasaporte_ocr` | OCR de pasaportes con Document AI |
| `procesar_nota_voz` | Transcripción de notas de voz WhatsApp |
| `enviar_notificacion_whatsapp_task` | Envío de WhatsApp a través de Evolution API |
| `check_passport_expiry` | Verificar pasaportes próximos a vencer |
| `check_client_birthdays` | Verificar cumpleaños del día |
| `check_pending_payments` | Enviar recordatorios de pago |
| `sync_bcv_rates` | Sincronizar tasas BCV |
| `backup_database_task` | Backup de PostgreSQL |
| `migrar_logos_agencia_task` | Migrar logos entre storages |

---

## 9. SISTEMA DE SEÑALES (SIGNALS)

### 9.1 Señales en `core/signals.py`

| Señal | Trigger | Acción |
|-------|---------|--------|
| `post_save` | `bookings.BoletoImportado` | `crear_o_actualizar_venta_desde_boleto`: Dispara parseo automático |
| `post_save` | `bookings.BoletoImportado` | `post_save_boleto_importado`: Post-parseo (notificaciones, etc.) |
| `post_save` | `bookings.PagoVenta` | `enviar_confirmacion_pago_recibido`: Notifica pago confirmado |
| `post_save` | `core.MigrationCheck` | `enviar_alerta_migratoria`: Alerta de migración |
| `pre_save` | `finance.Factura` | `capturar_pdf_factura_anterior`: Captura PDF antes de cambios |
| `post_save` | `finance.Factura` | `post_save_factura`: Envía a Telegram/WhatsApp |

### 9.2 Señales en `core/signals_audit.py`
Auditoría automática para modelos críticos: `PagoVenta`, `FeeVenta`, `Cliente`, `Proveedor`, etc.

### 9.3 Señales en `core/signals_contabilidad.py`
Señales para crear asientos contables automáticos desde facturas, pagos, etc.

### 9.4 Bypass de Señales (`core/signals_bypass.py`)
Mecanismo para desactivar señales temporalmente durante migraciones o procesos batch.

---

## 10. SEGURIDAD Y MIDDLEWARE

### 10.1 Orden de Middleware (`settings.py:140`)

```python
1. SecurityMiddleware          → Headers de seguridad básicos
2. WhiteNoiseMiddleware        → Servir archivos estáticos
3. SessionMiddleware           → Manejo de sesiones
4. CorsMiddleware              → CORS headers
5. CommonMiddleware            → Redirecciones, etc.
6. CsrfViewMiddleware          → Protección CSRF
7. AuthenticationMiddleware    → Autenticación de usuarios
8. AxesMiddleware              → Protección fuerza bruta
9. MultiTenantDomainMiddleware → Detección de agencia por dominio
10. ThreadLocalContextMiddleware → Contexto thread-local
11. SecurityHeadersMiddleware  → Headers de seguridad adicionales
12. MessageMiddleware          → Mensajes flash
13. XFrameOptionsMiddleware    → Clickjacking protection
14. SaaSLimitMiddleware        → Enforcement de cuotas SaaS
15. AIRateLimitMiddleware      → Rate limiting de IA
```

### 10.2 Medidas de Seguridad

- **CSP (Content-Security-Policy)**: Nonces rotativos por request (`context_processors.py`)
- **HSTS**: 1 año en producción
- **X-Frame-Options**: DENY en producción, SAMEORIGIN en desarrollo
- **Encryptación de campos**: `EncryptedCharField`/`EncryptedTextField` con Fernet (AES)
- **Rate Limiting**: DRF throttling + middleware específico de IA
- **Anti-fuerza bruta**: django-axes (5 intentos, 1h bloqueo)
- **Auditoría encadenada**: AuditLog con SHA-256 chain
- **Multi-tenancy**: Filtrado automático por agencia
- **Protección de datos**: No enviar PII a Sentry
- **Validación XSS**: bleach + template filters
- **Protección SSRF**: Validación de URLs en proxy Evolution API

### 10.3 Autenticación

| Método | Endpoint | Propósito |
|--------|----------|-----------|
| Session + Login | `/login/` | Admin y vistas HTML |
| JWT (simplejwt) | `/api/auth/jwt/obtain/` | APIs REST |
| Token (DRF) | `Authorization: Token xxx` | APIs automáticas |
| Magic Link | `/auth/magic/<token>/` | Login sin contraseña |

---

## 11. INTEGRACIONES EXTERNAS

| Integración | Archivos Clave | Propósito |
|-------------|---------------|-----------|
| **Google Gemini** | `apps/automation/parsers/gemini_parser.py`, `core/chatbot/` | IA para parseo y chatbot |
| **Stripe** | `apps/finance/views/stripe_views.py`, `apps/finance/services/` | Suscripciones SaaS |
| **Evolution API (WhatsApp)** | `core/views/evolution_qr_view.py`, `core/views/evolution_proxy_views.py` | WhatsApp Business |
| **Telegram Bot** | `core/management/commands/run_telegram_bot.py` | Notificaciones |
| **Resend (Email)** | `settings.py:438-453` | Envío de correos |
| **Gotenberg (PDF)** | `core/views/voucher_views.py` | Generación de PDFs |
| **Cloudflare R2** | `settings.py:217-246`, `core/storage.py` | Almacenamiento de archivos |
| **Amadeus API** | `core/views/flights_views.py` | Búsqueda de vuelos |
| **Unsplash** | `apps/marketing/services/` | Imágenes para marketing |
| **Cloudinary** | `settings.py:18-21` | Almacenamiento alternativo |
| **GCP Document AI** | `core/tasks.py` (procesar_pasaporte_ocr) | OCR de pasaportes |

---

## 12. FRONTEND Y TEMPLATES

### 12.1 Tecnologías Frontend
- **Renderizado**: Django Templates (SSR)
- **CSS**: TailwindCSS (via CDN o compilado local)
- **Interactividad**: HTMX (para acciones inline) + Alpine.js (para componentes)
- **Admin**: django-unfold (tema moderno sobre admin de Django)

### 12.2 Estructura de Templates

```
core/templates/              → Templates compartidos del core
apps/bookings/templates/     → Templates de ventas y reservas
apps/finance/templates/      → Templates de finanzas
apps/crm/templates/          → Templates de CRM
apps/contabilidad/templates/ → Templates de contabilidad
apps/cotizaciones/templates/ → Templates de cotizaciones
apps/marketing/templates/    → Templates de marketing
apps/cms/templates/          → Templates de CMS
apps/communications/templates/ → Templates de comunicaciones
templates/                   → Templates raíz (si existen)
```

### 12.3 Archivos Estáticos

```
static/                      → CSS, JS, imágenes
staticfiles/                 → Django collectstatic output
media/                       → Archivos subidos por usuarios (en desarrollo)
```

---

## 13. PRUEBAS (TESTS)

### 13.1 Configuración
- **Framework**: pytest + pytest-django
- **Config**: `pytest.ini` (settings: `travelhub.settings`, markers: slow/integration/unit/critical/vcr)
- **Coverage**: `--cov=.` via Makefile
- **Raíz**: `conftest.py` (importa de `tests/conftest.py`)

### 13.2 Makefile Commands
```bash
make test        # pytest tests/ --cov=. --cov-report=term-missing -v --create-db
make lint        # ruff check + black --check + isort --check-only
make format      # black . + isort .
make security    # check --deploy + safety + bandit
make migrate     # python manage.py migrate
```

### 13.3 Estructura de Tests
```
tests/                       → Tests globales
core/tests/                  → Tests del core
apps/bookings/tests/         → Tests de bookings
apps/finance/tests/          → Tests de finanzas
apps/cms/tests.py            → Tests de CMS
```

---

## 14. DESPLIEGUE (DOCKER)

### 14.1 Servicios (`docker-compose.yml`)

| Servicio | Imagen | Propósito |
|----------|--------|-----------|
| `traefik` | traefik:v3.0 | Proxy inverso + SSL |
| `db` | postgres:16-alpine | Base de datos |
| `redis` | redis:7-alpine | Cache + Broker |
| `web` | travelhub (build local) | Django + Gunicorn |
| `celery_worker` | travelhub (build local) | Worker de tareas |
| `celery_beat` | travelhub (build local) | Programador periódico |

### 14.2 Redes
- `travelhub_public`: traefik + web (acceso público)
- `travelhub_private`: db + redis + web + celery (aislado)

### 14.3 Variables de Entorno Clave (`.env`)
```
DATABASE_URL=postgresql://postgres:WZ5KfFD2.JSkhpGF.HJJHbUj@host.docker.internal:5433/TravelHub
CELERY_BROKER_URL=redis://127.0.0.1:6379/0
GEMINI_API_KEY=PLACEHOLDER_GEMINI_API_KEY
STRIPE_SECRET_KEY=sk_test_...
TELEGRAM_BOT_TOKEN=...
WHATSAPP_MICROSERVICE_TOKEN=travelhub_secret_token_2026
ENCRYPTION_KEY=maeDcrSC-aK7Wj5seM7vWnGuD7dXhfXB22YPzCT_CmQ=
RESEND_API_KEY=PLACEHOLDER_RESEND_API_KEY
```

### 14.4 Despliegue Local
```bash
# 1. Clonar repositorio
# 2. Crear .env con variables necesarias
# 3. Build y levantar
docker-compose up --build

# Sin Docker (desarrollo)
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements/base.txt
python manage.py migrate
python manage.py runserver 0.0.0.0:8000

# Celery (terminal separada)
celery -A travelhub worker --loglevel=info -Q default,notifications
celery -A travelhub beat --loglevel=info
```

---

## 15. GUÍA RÁPIDA PARA IA: CÓMO HACER CAMBIOS

### 15.1 Encontrar el Archivo Correcto

| Si necesitas... | Busca en... |
|----------------|------------|
| Cambiar un modelo de base de datos | `apps/<modulo>/models/` o `core/models/` |
| Crear/modificar una API REST | `apps/<modulo>/views/`, `core/serializers.py` |
| Modificar una URL/ruta | `travelhub/urls.py`, `apps/<modulo>/urls.py` |
| Cambiar la lógica de parseo | `apps/automation/parsers/` |
| Agregar una tarea programada | `travelhub/celery.py` o `core/tasks.py` |
| Modificar facturación | `apps/finance/models/facturacion.py`, `apps/finance/views/` |
| Cambiar autenticación | `core/views/auth_views.py` |
| Modificar middleware | `core/middleware.py`, `core/middleware_saas.py` |
| Agregar integración externa | Crear servicio en `apps/<modulo>/services/` |
| Modificar template HTML | `apps/<modulo>/templates/` o `core/templates/` |
| Cambiar configuración | `travelhub/settings.py` |
| Modificar tests | `apps/<modulo>/tests/` o `core/tests/` |
| Agregar parser de nuevo GDS | `apps/automation/parsers/<gds>_parser.py` + registry.py |

### 15.2 Reglas para Hacer Cambios

1. **Siempre heredar de `AgenciaMixin`** si el modelo necesita multi-tenancy.
2. **Siempre pasar `agencia`** como ForeignKey en nuevos modelos de negocio.
3. **Usar `tenant_task` decorator** para tareas Celery que operan en contexto de agencia.
4. **Usar `agency_context()` context manager** para tareas Celery que necesitan agencia.
5. **No importar modelos de `apps/` en `core/models/`** — hay dependencia circular.
6. **Usar `BoletoImportadoService`** para lógica de boletos (SRP).
7. **Usar `crear_audit_log()`** para registrar cambios importantes en datos.
8. **Usar `SoftDeleteModel`** para modelos que necesitan borrado lógico.
9. **Las URLs siguen convención REST**: `/recurso/`, `/recurso/nueva/`, `/recurso/<pk>/`.
10. **Views CRUD** usan `SaaSMixin` + `HtmxResponseMixin` para filtrado multi-tenant.

### 15.3 Patrón de Vista Típico

```python
# apps/<modulo>/views/<recurso>_views.py
class RecursoListView(SaaSMixin, HtmxResponseMixin, ListView):
    model = Recurso
    template_name = 'app/recurso_list.html'
    htmx_template_name = 'app/partials/_recurso_table.html'
    paginate_by = 20

class RecursoCreateView(SaaSMixin, HtmxResponseMixin, CreateView):
    model = Recurso
    form_class = RecursoForm
    template_name = 'app/recurso_form.html'

    def form_valid(self, form):
        form.instance.agencia = get_current_agency()
        return super().form_valid(form)
```

### 15.4 Patrón de Modelo Típico

```python
# apps/<modulo>/models/<modelo>.py
from core.models.base import AgenciaMixin, SoftDeleteModel

class MiModelo(AgenciaMixin, SoftDeleteModel, models.Model):
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True)
    activo = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Mi Modelo"
        verbose_name_plural = "Mis Modelos"
        ordering = ['-created_at']
        # Multi-tenancy automático via AgenciaMixin

    def __str__(self):
        return self.nombre
```

### 15.5 Patrón de Tarea Celery

```python
# apps/<modulo>/tasks.py
from celery import shared_task
from core.middleware import agency_context

@shared_task(name="apps.modulo.tasks.mi_tarea", time_limit=300, soft_time_limit=240, max_retries=3)
def mi_tarea(agencia_id, objeto_id):
    from core.models.agencia import Agencia
    agencia = Agencia.objects.get(pk=agencia_id)
    with agency_context(agencia):
        # Lógica aquí (ya tiene contexto de agencia)
        from .models import MiModelo
        obj = MiModelo.objects.get(pk=objeto_id)
        obj.procesar()
```

### 15.6 Flujo para Agregar Nuevo GDS Parser

1. Crear `apps/automation/parsers/<gds>_parser.py` heredando de `BaseParser`
2. Implementar método `parse(text: str) -> dict`
3. Registrar en `apps/automation/parsers/registry.py`
4. Agregar detección en `apps/automation/parsers/extraction.py`
5. Agregar tests en `core/tests/test_parser.py`
6. Ejecutar `make test`

---

> **Documentación generada para asistencia de IA — Mayo 2026**
> **TravelHub v2.0.0 — SaaS Multi-Tenant para Agencias de Viajes**

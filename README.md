# TravelHub 🚀

Plataforma de gestión SaaS multi-tenencia para agencias de viajes con automatización de boletos por IA, CRM, RAG vectorial, facturación multi-moneda, pasarela de pagos y notificaciones multicanal.

---

## 🏗️ Arquitectura General

- **Backend:** Django 5.x + Django REST Framework (DRF) + Python 3.12+
- **Capa Async & Tareas:** Celery + Redis 7
- **Base de Datos:** PostgreSQL 15 (con aislamiento multi-tenant por `Agencia`)
- **Frontend / Portal:** Django SSR + HTMX + Alpine.js + TailwindCSS / Admin Unfold
- **Seguridad:** Cifrado simétrico Fernet (API keys, credenciales), JWT, auditoría forense (`AuditLog`)
- **Motor Neuronal (IA):** Gemini 1.5 Pro/Flash (`google.genai`), OpenAI, DeepSeek (Provider Chain con fallback automático)
- **Base de Conocimientos RAG:** Vectorial de 768 dimensiones (`text-embedding-004`)

---

## 📦 Estructura de Aplicaciones

| Módulo / App | Descripción |
|---|---|
| `travelhub/` | Configuración central Django (settings local/prod, urls, wsgi, celery) |
| `core/` | Kernel público del dominio (`core.api`), modelos core, seguridad, cifrado, cuotas |
| `apps/bookings/` | Reservas, boletos aéreos (GDS Sabre, KIU, Amadeus), billing/suscripciones |
| `apps/crm/` | Gestión de clientes, pasajeros, historial de compras |
| `apps/finance/` | Facturación electrónica multi-moneda, comprobantes, pagos, comisiones |
| `apps/automation/` | Ingesta neuronal de boletos, Mailbot, RAG (`RAGKnowledgeService`) |
| `apps/communications/` | WhatsApp (Evolution API / Meta), Telegram Bot, Email (Resend) |
| `apps/contabilidad/` | Normativa tributaria venezolana (tasas BCV, retenciones IVA/ISLR) |
| `apps/cotizaciones/` | Presupuestos dinámicos e itinerarios |
| `apps/cms/` | Base de conocimiento (`KBDocument`, `KnowledgeChunk`) y contenido |
| `apps/gamification/` | Recompensas, metas de ventas y puntajes |
| `apps/reports/` | KPIs financieros, reportes programados en PDF |
| `tests/` | Suite con 65+ tests unitarios, de integración y E2E (pytest) |

---

## ⚡ Nuevas Funcionalidades SaaS B2B

### 1. Autoservicio & Suscripciones (`SuscripcionService`)
- **Self-Service Onboarding (`POST /api/auth/register-tenant/`):** Alta atómica de agencias, usuarios propietarios y configuración inicial.
- **Planes Escalonados:** `FREE` (50 boletos/mes), `BASIC` (300 boletos/mes), `PRO` (1500 boletos/mes), `ENTERPRISE` (Ilimitado).
- **Consulta de Consumos (`GET /api/billing/current-plan/`):** Métrica en tiempo real del % de cuota consumida.
- **Pasarela Checkout (`POST /api/billing/checkout/`):** Upgrades instantáneos por Stripe Sandbox, Zelle o PagoMóvil.

### 2. Motor RAG & Base de Conocimiento (`RAGKnowledgeService`)
- Indexación vectorial avanzada (`text-embedding-004`).
- **Compendio de Turismo & Manuales GDS:** Incluye manuales de Sabre, Amadeus, KIU, regulaciones migratorias SAIME/INAC, guías de Los Roques, Nueva Esparta y directorio aéreo.
- **Comando de Ingesta:**
  ```bash
  python manage.py ingest_folder_manuals --dir docs/manuales_notebooklm
  ```

### 3. Notificación Automática Multicanal
Al generar o procesar un boleto PDF, el sistema despacha automáticamente:
- **Telegram Bot:** PDF y ficha técnica al canal de la agencia (`send_telegram_document_task`).
- **WhatsApp:** Envío automático del boleto PDF al cliente (`WhatsAppService.send_document`).

---

## 🛠️ Inicio Rápido

```bash
# 1. Clonar el repositorio
git clone <repo-url>
cd travelhub_project

# 2. Configurar entorno virtual e instalar dependencias
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt

# 3. Configurar variables de entorno
cp .env.example .env

# 4. Ejecutar migraciones de base de datos
python manage.py migrate

# 5. Iniciar servidor de desarrollo
python manage.py runserver
```

---

## 🧪 Pruebas & Calidad de Código

Ejecución de la suite completa de pruebas unitarias e integración con `pytest`:

```bash
# En entorno con SQLite de prueba
$env:USE_SQLITE_TEST_DB="true"; python -m pytest tests/

# En entorno Docker con PostgreSQL
docker compose -f docker-compose.test.yml run --rm web pytest tests/
```

- **Pre-commit Hooks:** Linters `ruff`, `ruff-format` e inspección de importaciones cruzadas prohibidas (`check-domain-imports`) activos al 100%.

---

## 📊 Monitoreo & Telemetría

- **Dashboard de Estado:** `http://localhost:8000/system/status/`
- **Healthcheck JSON:** `http://localhost:8000/health/`
- **Métricas Avanzadas:** `http://localhost:8000/health/metrics/`
- **Prometheus Metrics:** `http://localhost:8000/prometheus/`
- **Alertas en Vivo:** Integración con Sentry (`SENTRY_DSN`) y Telegram Bot.

# TravelHub

Plataforma de gestión de agencias de viajes multi-tenencia con automatización, CRM, facturación electrónica y más.

## Arquitectura

- Django + PostgreSQL + Redis + Celery
- Multi-tenencia (por agencia)
- Panel admin con Unfold
- API REST con DRF

## Estructura del proyecto

| Directorio | Descripción |
|---|---|
| `travelhub/` | Configuración Django (settings, urls, wsgi, celery) |
| `core/` | Módulo central (modelos, servicios, admin, seguridad, cifrado) |
| `apps/bookings/` | Gestión de reservas, boletos aéreos, hoteles, autos |
| `apps/crm/` | Gestión de clientes, historial, relaciones |
| `apps/finance/` | Facturación electrónica, conciliación, comisiones |
| `apps/automation/` | Automatización con IA, proveedores Gemini/OpenAI/DeepSeek |
| `apps/communications/` | Notificaciones email (Resend), WhatsApp, Telegram |
| `apps/contabilidad/` | Contabilidad venezolana (BCV, IVA, fiscal) |
| `apps/cotizaciones/` | Cotizaciones y presupuestos |
| `apps/cms/` | Gestión de contenido (artículos) |
| `apps/gamification/` | Gamificación, logros, puntajes |
| `apps/marketing/` | Campañas de marketing |
| `apps/reports/` | Reportes programados y KPIs |
| `apps/tasks/` | Tareas internas |
| `tests/` | Tests unitarios, de servicios, E2E Playwright |

## Requisitos

- Docker y Docker Compose
- Python 3.12+
- PostgreSQL 15, Redis 7

## Inicio rápido

```bash
# Clonar
git clone <repo>
cd travelhub

# Variables de entorno
cp .env.example .env
# Editar .env con tus claves

# Iniciar con Docker
docker compose up -d

# Migraciones
docker compose exec web python manage.py migrate

# Tests
docker compose -f docker-compose.test.yml run --rm web
```

## Tests

- Framework: pytest
- Cobertura mínima: 75% (`--cov-fail-under=75`)
- Tests unitarios: `pytest tests/unit/`
- Tests servicios: `pytest tests/services/`
- Tests E2E: `pytest tests/e2e/` (requiere `E2E_TESTS=1`)
- Ver cobertura: `pytest --cov=. --cov-report=term-missing`

### CI/CD

GitHub Actions ejecuta:
1. Pre-check rápido en `tests/unit/`
2. Suite completa con PostgreSQL service
3. Verificación de cobertura >= 75%

## Características principales

- **Multi-tenencia**: Agencias aisladas con cifrado de datos sensibles
- **IA integrada**: Gemini, OpenAI, DeepSeek con fallback automático
- **GDS**: Parsers para Sabre, KIU, Amadeus
- **Facturación**: Factura electrónica venezolana (SENIAT/IVSS)
- **BCV**: Tasas de cambio del Banco Central de Venezuela
- **Notificaciones**: Email (Resend), WhatsApp (Evolution API), Telegram
- **Seguridad**: Cifrado Fernet, API keys rotables, auditoría, SSO
- **Dashboard admin**: Panel unificado con monitoreo de salud del sistema

## Despliegue

- Producción: Docker Compose con Nginx, Gunicorn, Uvicorn
- Base de datos: PostgreSQL 15 (RDS en AWS)
- Cache: Redis 7 (ElastiCache)
- Archivos: R2 (Cloudflare) o S3

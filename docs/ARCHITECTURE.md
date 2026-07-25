# TravelHub Architecture

## Overview

TravelHub is a multi-tenant travel agency management platform built with Django.
It manages bookings, CRM, financial operations, AI-powered automation, and communications.

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend | Django 5.1 + Python 3.12 |
| Database | PostgreSQL 15 |
| Cache | Redis 7 |
| Task Queue | Celery + Redis |
| API | Django REST Framework |
| Admin | Django Admin + Unfold theme |
| AI | Google Gemini, OpenAI, DeepSeek |
| Email | Resend API |
| WhatsApp | Evolution API |
| Container | Docker + Docker Compose |
| Proxy | Nginx |
| ASGI/WSGI | Uvicorn + Gunicorn |

## Project Structure

```
travelhub/                  # Django project configuration
├── settings/               # Settings by environment
│   ├── base.py             # Base settings (shared)
│   ├── development.py      # Local dev settings
│   ├── production.py       # Production settings
│   └── testing.py          # Test settings
├── urls.py                 # Root URL configuration
├── celery.py               # Celery app
└── wsgi.py / asgi.py       # WSGI/ASGI entry points

core/                       # Core module
├── models/                 # Django models (Agencia, User, etc.)
├── views/                  # View layer
├── services/               # Business logic layer
├── admin/                  # Admin panel configuration
├── security.py             # Tenant isolation, permissions
├── fields.py               # Encrypted fields (Fernet)
├── validators.py           # File validators
├── storage.py              # File storage abstraction
└── middleware.py            # Django middleware

apps/                       # Django applications
├── bookings/               # Booking management (flights, hotels, cars)
├── crm/                    # Customer relationship management
├── finance/                # Invoicing, reconciliation, payments
├── automation/             # AI providers, parsers, automation
│   ├── providerchain/      # Gemini, OpenAI, DeepSeek + fallback
│   ├── services/           # AI engine, parsers, tools
│   └── parsers/            # Ticket parsers (Sabre, Amadeus, etc.)
├── communications/         # Email, WhatsApp, Telegram, notifications
├── contabilidad/           # Venezuelan accounting (BCV, IVA, fiscal)
├── cotizaciones/           # Quotes and budgets
├── cms/                    # Content management
├── gamification/           # Gamification (points, achievements)
├── marketing/              # Marketing campaigns
├── reports/                # Scheduled reports and KPIs
├── tasks/                  # Internal tasks
└── common/                 # Shared utils, services, tasks

tests/                      # Test suite
├── unit/                   # Unit tests (no DB)
├── services/               # Service layer tests
├── views/                  # View smoke tests
├── admin/                  # Admin panel tests
├── e2e/                    # End-to-end (Playwright)
├── integration/             # Integration tests
├── parsers/                # GDS parser tests
├── fixtures/               # Test fixtures
├── helpers.py              # Factory functions
└── conftest.py             # Shared fixtures
```

## Key Design Patterns

### Multi-tenancy
- Each `Agencia` is isolated
- All models have `agencia` foreign key
- Middleware sets `request.agencia` from authenticated user
- Superusers have cross-agency access
- `filter_queryset_by_tenant()` applies agency filter automatically

### AI Provider Chain
- Abstract `AbstractBaseProvider` defines interface
- Concrete providers: `GeminiProvider`, `OpenAIProvider`, `DeepSeekProvider`
- `FallbackRouter` tries providers in priority order
- Circuit breaker prevents hammering failing providers
- `ProviderRegistry` manages provider lifecycle
- Usage metrics tracked via `tracing.py`

### Encryption
- `EncryptedCharField` / `EncryptedTextField` use Fernet symmetric encryption
- `ENCRYPTION_KEY` setting required
- Keys are 4x storage overhead
- Lazy initialization of Fernet instance

### Security
- API Secrets stored encrypted with Fernet
- Tenant isolation enforced at query level
- Audit logging for all critical operations
- Row-level security (RLS) for PostgreSQL
- SSO support
- Rate limiting on AI endpoints

## Data Flow

1. **Request** → Nginx → Gunicorn/Uvicorn → Django middleware → View
2. **Middleware** sets agency context, enforces tenant isolation, checks quotas
3. **View** delegates to Service layer → returns Response
4. **Service** orchestrates business logic, calls external APIs, returns results
5. **AI Parser** receives ticket text → sends to Gemini/OpenAI → returns structured data
6. **Notification** dispatches via Email (Resend) or WhatsApp (Evolution API)

## Testing Strategy

- **Unit tests**: Pure logic, no DB (core validators, security, fields)
- **Service tests**: Business logic with mocked external APIs
- **View smoke tests**: URL resolution, status code checks
- **Admin tests**: Admin registration, display configuration
- **E2E tests**: Playwright for critical user flows (CI=1 conditional skip)
- **Coverage threshold**: 75% minimum

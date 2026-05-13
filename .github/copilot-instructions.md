# Copilot Instructions for TravelHub

Concise project-specific guidance for AI coding agents. Focus on existing patterns; avoid inventing new architectural styles unless explicitly requested.

## Big Picture
TravelHub is a Spanish-language Django 5.2 + DRF SaaS backend with an HTMX + Alpine.js + TailwindCSS frontend (SSR templates in `templates/` and `core/templates/`). Domain = travel agency CRM/ERP/CMS: sales (`Venta`), accounting (`AsientoContable`), invoices (`Factura`), ticket ingestion & normalization (GDS parsers KIU/Sabre/Amadeus/Copa/Wingo/TKConnect), and CMS pages. Core logic lives in `core/` (models, parsers, PDF generation via Gotenberg, audit logging). SQLite used locally; Postgres via `docker-compose` for production.

## Architecture & Data Flow
1. File (PDF/TXT/EML) upload -> `BoletoImportado` model instance -> Celery task `parsear_boleto_individual()` -> `TicketParserService` orchestrates: extraction, AI/GDS parsing, normalization, persistence -> `VentaAutomationService` creates `Venta` -> PDF generation via Gotenberg -> notifications (WhatsApp/Telegram/Email).
2. Financial core: `Venta` aggregates `ItemVenta` via signals (`post_save`) to recalc totals & state. State machine: `PENDIENTE_PAGO -> PAGADA_PARCIAL -> PAGADA_TOTAL -> CONFIRMADA -> EN_PROCESO_VIAJE -> COMPLETADA`.
3. Audit trail: `AuditLog` with hash chaining (`previous_hash`/`record_hash`) provides tamper evidence. `_crear_audit_log()` centralized in `core/models/audit.py`.
4. Multi-tenancy via `AgenciaMixin` + `AgenciaManager` (auto-filters by agency). Thread-local context via `ThreadLocalContextMiddleware`. Never use `objects.all()` without tenant context.

## Key Conventions
- Language: models, fields, API responses in Spanish. Keep new identifiers consistent (snake_case, Spanish).
- Monetary consistency: when fare + taxes != total (tolerance 0.01) parser sets `amount_consistency='MISMATCH'`.
- Security headers & CSP via `SecurityHeadersMiddleware`; template JS needs `nonce` from `request.META['CSP_NONCE']`.
- PDF templates: Gotenberg renders HTML templates from `core/templates/core/tickets/`. One template per GDS system.
- Encryption: `core/fields.py` `EncryptedCharField`/`EncryptedTextField` require `ENCRYPTION_KEY` in settings.

## Developer Workflows
Backend: `pip install -r requirements/local.txt` -> `python manage.py migrate` -> `python manage.py runserver`.
Optional Postgres: `docker-compose up -d db redis` then set env vars from `.env.example`.
Tests: `pytest -q` (CI threshold 77%), `ruff check .` and `ruff format .` for lint/format.

## DRF Patterns
- ViewSets in `core/views/` and `apps/*/views/`. Access control uses `TenantViewSetMixin` for multi-tenancy.
- Custom throttles: `DashboardRateThrottle`, `LiquidacionRateThrottle`, `ReportesRateThrottle`, `UploadRateThrottle`, `AIParserDailyQuotaThrottle`.

## Parsing & Normalization
- Orchestrator: `apps/automation/services/ticket_parser_service.py` `TicketParserService`.
- AI parser: `apps/automation/parsers/ai_universal_parser.py` `UniversalAIParser` uses Gemini with structured Pydantic schemas.
- Legacy parsers: `apps/automation/parsers/registry.py` `ParserRegistry` manages Sabre, KIU, Amadeus, Copa, Wingo, TKConnect parsers.
- Normalization: `apps/automation/parsers/normalization.py` `DataNormalizationService` handles field aliasing, IATA city mapping, time normalization.

## Multi-tenancy
- `AgenciaMixin` on all tenant-scoped models. `AgenciaManager` auto-filters.
- `ThreadLocalContextMiddleware` sets `request.agencia` and PostgreSQL RLS context.
- `SaaSMixin` for class-based views, `get_agencia_from_request()` for function-based.
- Admin uses `SaaSAdminMixin` for tenant isolation in Django admin.

## Signals & Automation
- `core/signals.py`: ticket processing, sale creation, payment confirmations, migration alerts.
- `core/signals_audit.py`: audit logging for Venta, ItemVenta, Pasajero, Factura.
- `core/signals_contabilidad.py`: automatic accounting entries from financial events.
- `core/signals_passport.py`: auto-OCR passport processing.

## What NOT To Do
- Don't rename existing JSON keys used by parsers or PDF templates without migration plan.
- Don't introduce new lint/format tools; use ruff only.
- Don't bypass multi-tenancy or audit hash chaining.
- Don't create new Next.js or frontend code; the frontend is HTMX + Alpine.js SSR.

## Good First Enhancements (if asked)
- Add tests for uncovered parser edge cases.
- Improve Gotenberg health check resilience.
- Add structured logging with structlog.

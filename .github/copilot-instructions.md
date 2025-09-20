# Copilot Instructions for TravelHub

Concise project-specific guidance for AI coding agents. Focus on existing patterns; avoid inventing new architectural styles unless explicitly requested.

## Big Picture
TravelHub is a Spanish‑language Django 5 + DRF backend with a Next.js (App Router) TypeScript frontend (`frontend/`). Domain = travel agency CRM/ERP/CMS: sales (`Venta`), accounting (`AsientoContable`), invoices (`Factura`), ticket ingestion & normalization (GDS parsers KIU/Sabre, future Amadeus/Travelport), and lightweight CMS pages & packages. Core logic lives in `core/` (models, parsers, PDF generation, audit logging). SQLite used locally; Postgres via `docker-compose` for production.

## Architecture & Data Flow
1. File (PDF/TXT/EML) upload -> `BoletoImportado` model instance -> signal `trigger_boleto_parse` -> `parsear_boleto()` -> `ticket_parser.extract_data_from_text()` & specialized KIU/Sabre logic -> raw dict + `normalized` sub-dict -> optional `VentaParseMetadata` snapshot -> PDF generation (`core/pdf_generator.generate_ticket_pdf()` or legacy KIU path) -> stored in `archivo_pdf_generado`.
2. Financial core: `Venta` aggregates `ItemVenta` + `FeeVenta` + `PagoVenta` via signals (`post_save`) to recalc totals & state, and to award loyalty points (1 per 10 currency units) once fully paid / completed. State machine distinguishes financial (`PEN/PAR/PAG`) vs operational (`CNF/VIA/COM/CAN`).
3. Audit trail: `_crear_audit_log` invoked from `Venta.save`, `ItemVenta.save`, delete signals, and state transitions. Hash chaining (`previous_hash`/`record_hash`) provides tamper evidence.
4. Extended components (multi-product) attach to `Venta` via related names: `alquileres_autos`, `eventos_servicios`, `circuitos_turisticos` (with `dias` children), `paquetes_aereos`, `servicios_adicionales`, etc. DRF serializers expose them read‑only inside `VentaSerializer`.
5. PDF ticket templates selected by GDS in `pdf_generator.select_template_and_data`; Sabre path transforms structured flights; KIU/others use legacy normalized keys.

## Key Conventions
- Language: models, fields, and API responses mostly Spanish; keep new identifiers consistent (snake_case, Spanish descriptive names). Enums use short uppercase codes.
- Do not remove original parse fields; `normalized` adds abstraction without deleting raw keys.
- Monetary consistency: when fare + taxes != total (tolerance 0.01) parser sets `amount_consistency='MISMATCH'` and differences fields; keep this contract if adding new parsers.
- Loyalty points logic only mutates once; respect `puntos_fidelidad_asignados` guard.
- Security headers & CSP via `SecurityHeadersMiddleware`; any template JS needs `nonce` from `request.META['CSP_NONCE']`.
- New PDF templates must mirror semantic structure (`ticket-header/body/footer`) and add color palette variables in `:root` per GDS.

## Developer Workflows
Backend local quick start: create venv -> `pip install -r requirements-dev.txt` (if present) or `requirements.txt` -> `python manage.py migrate` -> `python manage.py runserver`. Optional Postgres: `docker-compose up -d db` then set env vars from `.env.example`.
Tests & quality: `pytest -q` (coverage target gradually increasing; current baseline 71%), `ruff check .` and `ruff format .` for lint/format. Dependency audit via `pip-audit` (used in CI). Frontend: `npm install && npm run dev` (expects API at 8000; env `NEXT_PUBLIC_API_BASE_URL`).

## DRF Patterns
- ViewSets reside in `core/views.py` with straightforward `ModelViewSet`. Access control uses custom `IsStaffOrGroupWrite` allowing write for staff or group names containing 'oper'/'venta'. Keep that pattern for new component endpoints.
- Nested collections inside `VentaSerializer` are read‑only lists; creation/update of items happens via separate endpoints except `items_venta` (write-enabled inside `VentaSerializer`). Follow this split if adding more child models.

## Parsing & Normalization
- Central parser file: `core/ticket_parser.py` (large; search for Sabre/KIU detection). Add new GDS detection heuristics before fallback error message. Always populate `SOURCE_SYSTEM`, and fill `normalized` with base contract (see README section "Contrato de Normalización") plus `segments` list.
- Dates: provide both human (`DD-MM-YYYY`) and ISO (`YYYY-MM-DD`) variants; infer arrival +1 day if arrival time earlier than departure.
- CO2 emissions pattern recognized (e.g. `397.86 kg CO2`); preserve logic if extending.

## Signals & Side Effects
- Avoid double-financial recalculations: `Venta.recalcular_finanzas()` is invoked by `FeeVenta` & `PagoVenta` post_save signals; do not call it redundantly inside those model saves.
- When adding new monetary-impacting related models, either integrate into `recalcular_finanzas` or keep them separate; comment clearly.

## Audit Logging
- Use `_crear_audit_log(modelo=..., accion=AuditLog.Accion.CREATE/UPDATE/DELETE/STATE, venta=<Venta?>, descripcion=..., metadata_extra={})`.
- For UPDATE diffs, follow existing pattern: store changed fields under `metadata_extra.diff` with `{campo: {antes, despues}}`.

## Extending Ticket PDFs
- For new GDS: implement transformation akin to `transform_sabre_data_for_template`; add template `core/templates/core/tickets/ticket_template_<gds>.html`; map color palette; update `select_template_and_data` case.

## What NOT To Do
- Don’t rename existing JSON keys used by frontend, parsers, or PDF templates without migration plan.
- Don’t introduce new lint/format tools; use ruff only.
- Don’t bypass loyalty points guard or modify audit hash chaining approach.

## Good First Enhancements (if asked)
- Add Amadeus parser skeleton returning `normalized` with TODO markers.
- Add tests increasing coverage for monetary mismatch edge cases.

(End of file – ask user before large refactors or new subsystems.)

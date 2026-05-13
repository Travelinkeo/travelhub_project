# Arquitectura del Sistema TravelHub

**Última Actualización:** Mayo 2026

## 1. Visión General

TravelHub es una plataforma SaaS B2B multi-tenant para agencias de viajes. Opera como un **Monolito Modular** sobre Django 5.2.6 (Python 3.13), priorizando simplicidad operativa y ACID garantizado.

## 2. Stack Tecnológico

| Capa | Tecnología |
|------|-----------|
| Backend | Django 5.2.6 + Django REST Framework |
| Frontend | TailwindCSS + HTMX + Alpine.js (HTML-over-the-wire SSR) |
| Base de Datos | PostgreSQL 16 (producción), SQLite (desarrollo) |
| Cache/Broker | Redis 7 |
| Async Tasks | Celery 5.5 con 4 colas: default, ia_fast, ia_heavy, notifications |
| IA | Google Gemini (genai SDK v1.x) — motor unificado en `AIEngine` |
| PDF | Gotenberg (headless Chromium para HTML→PDF) |
| Billing | Stripe (SaaS): FREE, BASIC ($29), PRO ($99), ENTERPRISE ($299) |
| Comunicaciones | Evolution API (WhatsApp), Resend (email), Telegram Bot |
| Almacenamiento | Cloudinary / Cloudflare R2 / Local (configurable) |
| Infraestructura | Docker Compose, WSL2, Cloudflare Tunnel |

## 3. Arquitectura Multi-tenant

### AgenciaMixin (Capa de Datos)
Todos los modelos de negocio heredan de `AgenciaMixin`. El `AgenciaManager` personalizado filtra automáticamente por `agencia` en cada query. Para bypass (superadmin/migraciones), usar `.all_objects`.

### ThreadLocalContextMiddleware (Capa de Contexto)
Captura la agencia del usuario autenticado en cada request y la almacena en thread-local storage. Disponible globalmente vía `get_current_agency()`.

### SaaSAdminMixin (Capa Admin)
Extiende el admin de Django con filtrado automático por agencia, ocultando el campo `agencia` y restringiendo dropdowns a los registros del mismo tenant.

### PostgreSQL RLS
Políticas `tenant_isolation_policy` y `superadmin_bypass` a nivel de base de datos como segunda capa de defensa.

## 4. Apps del Proyecto

```
apps/
├── automation/    — Parsing de boletos, AI Engine, OCR, voice parsing
├── bookings/      — Ventas, reservas, boletos, tarifarios
├── cms/           — Blog, guías de destino, posts para redes
├── common/        — Catálogos (países, ciudades, aerolíneas) y servicios compartidos
├── communications/— Email, WhatsApp, Telegram, notificaciones
├── contabilidad/  — Plan contable, asientos, reportes (VEN-NIF)
├── cotizaciones/  — Cotizaciones pre-venta, Magic Quoter
├── crm/           — Clientes, pasajeros, leads Kanban
├── finance/       — Facturación, comisiones, conciliaciones
├── marketing/     — Campañas, flyers, copywriting IA
core/              — Núcleo: modelos base, middleware, seguridad, auditoría
```

## 5. Flujo de Datos Crítico — Procesamiento de Boletos

```
Email (IMAP/Resend Webhook)
  → BoletoImportado (modelo)
  → Celery: parsear_boleto_individual()
  → ExtractionService (PDF/TXT/EML → texto)
  → TicketParserService (orquestador)
    → UniversalAIParser (Gemini + Pydantic schemas)
    → Fallback: parsers legacy (Sabre, KIU, Amadeus, Copa, Wingo, TKConnect)
  → DataNormalizationService
  → VentaAutomationService (crea Venta + ItemVenta + SegmentoVuelo)
  → PdfGenerationService (Gotenberg → PDF)
  → Notificaciones (WhatsApp/Telegram/Email)
```

## 6. Seguridad

| Mecanismo | Implementación |
|-----------|---------------|
| CSP | `SecurityHeadersMiddleware` con nonces rotativos por request |
| HSTS | 1 año, includeSubdomains, preload |
| X-Frame-Options | DENY |
| Encriptación | `EncryptedCharField`/`EncryptedTextField` con Fernet (ENCRYPTION_KEY) |
| Rate Limiting | DRF throttles + `AIRateLimitMiddleware` por plan |
| Fuerza Bruta | django-axes: 5 intentos, 1h bloqueo |
| Auditoría | `AuditLog` con encadenamiento SHA-256 |
| God Mode | Impersonación con timeout 30min, rate limit 5/hora, auditoría forense |

## 7. Despliegue

### Desarrollo
```bash
pip install -r requirements/local.txt
python manage.py migrate
python manage.py runserver
```

### Producción
```bash
cp .env.example .env  # Editar con valores reales
docker-compose up --build -d
cloudflared tunnel --url http://localhost:8000
```

Ver [Guía de Despliegue](deployment/DEPLOYMENT.md) para instrucciones completas.

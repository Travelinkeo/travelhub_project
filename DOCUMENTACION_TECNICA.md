
# TravelHub Technical Analysis & Architecture

## 1. Executive Summary
TravelHub is a specialized **ERP/SaaS solution for Travel Agencies**, built to automate the complex workflows of ticketing, invoicing, and customer management. Its value proposition lies in its **"Zero-Click" automation**: ingestion of GDS emails (Amadeus, Sabre, Kiu), AI-powered extraction, and automatic reconciliation of financial records.

This document provides a technical deep-dive into the architecture, intended for Engineering Leads, AI Agents, and scalable system architects.

---

## 2. High-Level Architecture

The system follows a **Monolithic Service-Oriented Architecture (SOA)** pattern within Django. While deployed as a single unit, the internal logic is decoupled into Service layers, separated from Views (Presentation) and Models (Data).

```mermaid
graph TD
    User[Web User / Travel Agent]
    GDS[GDS Email Systems]
    Whatsapp[WhatsApp API]
    
    subgraph "TravelHub Application Layer"
        UI[Frontend: Django Templates + HTMX + Tailwind]
        API[API Layer: DRF ViewSets]
        
        subgraph "Ingestion Engines"
            MailBot[Email Bot Daemon\n(IMAP + Gmail IO)]
            VisionAI[Passport & Ticket OCR\n(Google Gemini Vision)]
        end
        
        subgraph "Core Business Logic (Services)"
            TicketService[TicketParserService\n(Regex + LLM Hybrid)]
            InvoiceService[FacturacionService\n(Fiscal Logic)]
            MarketingService[MarketingAI\n(Content Gen + Pillow)]
        end
        
        subgraph "Data Persistence"
            DB[(PostgreSQL / SQLite)]
            Cloud[(Cloudinary / S3\nMedia Storage)]
        end
    end

    GDS -->|Ticket EML/PDF| MailBot
    MailBot --> TicketService
    TicketService --> DB
    User --> UI
    UI --> API
    API --> VisionAI
    InvoiceService --> DB
    TicketService -->|Success Signal| Whatsapp
```

---

## 3. Technology Stack

### Backend Core
- **Language**: Python 3.12+ (Type Hinting applied).
- **Framework**: Django 5.x (MTV Pattern).
- **API**: Django Rest Framework (DRF) for React/Mobile integration.
- **Asynchronous Processing**:
    - Current: Threaded Management Commands (`run_email_bot --loop`).
    - Recommendation: Celery + Redis for robustness.

### Frontend
- **Templating**: Django Template Language (DTL).
- **Interactivity**: **HTMX** (Hypermedia-driven dynamic UI without heavy JS bundles).
- **Styling**: **TailwindCSS** (Utility-first).
- **Components**: AlpineJS (lightweight state) + Hyperscript (interactions).

### Artificial Intelligence & Automation
- **LLM/Vision**: Google **Gemini Pro 1.5** & **Gemini Vision**.
    - Used for: Ticket parsing (unstructured PDFs), Passport Data Extraction, Hotel Rate Sheet Analysis.
- **Generative Image**: Pillow (Python Imaging Library) for programmatic marketing assets.

### Infrastructure (Current/Recommended)
- **Database**: SQLite (Dev) -> **PostgreSQL** (Production).
- **Storage**: `FileSystemStorage` (Local) -> **Cloudinary** (Production Media).
- **Hosting**: VPS (Coolify/Docker) or PaaS (Render/Heroku/Railway).

---

## 4. Core Modules & Services

### A. The Ingestion Engine (`EmailBot`)
*Located in: `core/management/commands/run_email_bot.py`*
A continuously running daemon that monitors Gmail via IMAP.
- **Filters**: Scans only `UNSEEN` emails with keywords (TICKET, EMISION, FACTURA).
- **Logic**: 
    1. Extracts Attachments (PDF/HTML).
    2. Uploads raw PDF to Cloudinary.
    3. Triggers `TicketParserService`.
    4. Upon success, marks email as `\Seen` and replies to support.

### B. The Hybrid Parser (`TicketParserService`)
*Located in: `core/services/ticket_parser_service.py`*
A sophisticated multi-strategy extraction engine:
1.  **Regex Strategy (Fast)**: Attempts to match known GDS patterns (Amadeus/Sabre/Kiu).
2.  **LLM Strategy (Fallback/Smart)**: If Regex fails, sends text/PDF to **Gemini AI** with a structured prompt to extract structured JSON.
3.  **Normalization**: Standardizes Airline Names, Dates, and Monies into a canonical format.

### C. Financial Core (`FacturacionService` / `DobleFacturacion`)
*Located in: `core/services/doble_facturacion.py`*
Handles complex Venezuelan fiscal requiremens:
- **Split Billing**: Automatically splits a ticket sale into two invoices:
    - **Third Party**: Use of stored airline funds.
    - **Fee/Commission**: Agency revenue (Taxable).
- **Currency**: Multi-currency support (USD/VES) with BCV rate integration.

### D. Marketing & Content (`MarketingService` / `AI Copywriter`)
*Located in: `core/services/marketing_service.py`*
- **Canvas Engine**: Generates Instagram Stories dynamically from `Hotel` or `Package` data.
- **Copywriter**: Uses LLM to write sales copy for WhatsApp/Instagram captions.

---

## 5. Critical Workflows (Data Flow)

### "From E-Mail to Cash" (The Zero-Click Flow)
1.  **Trigger**: GDS sends email with PDF ticket to `boletos@travelinkeo.com`.
2.  **Ingest**: `EmailBot` detects email, downloads PDF.
3.  **Process**: `TicketParserService` extracts metadata (PNR `ABC123`, Passenger `DOE/JOHN`, Amount `$500`).
4.  **Persist**: 
    - **Semáforo Migratorio**: Validación de requisitos de viaje [Ver Docs](MIGRATION_CHECKER.md).
    - **Procesamiento de Boletos**: Extracción de datos con Regex/IA.
    - **Signal**: Triggers `post_save`.
    - Creates `Venta` (Sale Record) automatically assigned to the correct Client/Agency.
5.  **Notify**: `WhatsAppService` sends a message to the Agent: "New Ticket Processed: ABC123" with the Cloudinary link.

---

## 6. Analysis & Weaknesses (The "Audit")

### Strengths
- **Agility**: HTMX + Django allows for extremely fast feature development.
- **Innovation**: Real integration of Vision AI for "boring" tasks (OCR) is a major competitive advantage.
- **Business Logic**: The fiscal logic (`DobleFacturacion`) is highly specialized and valuable.

### Weaknesses vs. Scalability Risks
1.  **The "Loop" Bot**: Running a management command `while True` is fragile. If the container restarts, the bot dies. 
    - *Fix*: Move to **Celery Beat** or a robust Supervisor process.
2.  **Duplicate Handling**: The collision logic for PNRs is basic. Large agencies often re-issue tickets (re-pricing). 
    - *Fix*: Implement versioning for Tickets (V1, V2) instead of blocking duplicates.
3.  **Test Coverage**: Unit tests are sparse. Critical financial logic relies on manual verification.
    - *Fix*: Add `pytest` for the `facturacion` and `parser` services.
4.  **Logging**: Currently mixed (`print` vs `logger`). Needs centralized Sentry integration.

## 7. Future Roadmap for "LINKEO" (The Chatbot)
To build **LINKEO** as an intelligent assistant, it should interface with the **Service Layer**, not the Models directly.
- **Capabilities needed**:
    - "Linkeo, did we sell any tickets to Madrid today?" -> Queries `VentaService`.
    - "Linkeo, resend the PDF for PNR ABC123." -> Calls `WhatsAppService`.
    - "Linkeo, draft a promo for Hotel X." -> Calls `MarketingService`.

This architecture supports "Function Calling" (Tools) natively, making an AI agent integration straightforward.

# Arquitectura del Sistema TravelHub

**Versión del Documento:** 1.0
**Última Actualización:** 28 de Noviembre de 2025

## 1. Visión General
**TravelHub** es una plataforma SaaS (Software as a Service) diseñada para la gestión integral de agencias de viajes. Su objetivo es modernizar y automatizar el flujo de trabajo operativo, desde la recepción de boletos aéreos hasta la facturación y el análisis financiero.

El sistema opera como un **Monolito Modular** construido sobre Django, priorizando la simplicidad operativa y la robustez financiera (VEN-NIF).

## 2. Stack Tecnológico

### Backend (El Motor)
*   **Framework:** Django 5.2.6 (Python 3.13.5).
*   **Base de Datos:** PostgreSQL.
*   **Asincronía:** Celery + Redis (para procesamiento de emails y tareas pesadas).
*   **Parsing:** Motor propio basado en Regex (`core/ticket_parser.py`) para extracción de datos de boletos (KIU, Sabre, Amadeus).

### Frontend (La Interfaz)
*   **Enfoque:** HTML-over-the-wire (Renderizado en Servidor).
*   **Estilos:** TailwindCSS (vía CDN en dev, build process pendiente).
*   **Interactividad:** HTMX (para AJAX sin JS complejo) + Alpine.js (para UI interactiva).
*   **Diseño:** Glassmorphism / Dark Mode por defecto.

### Infraestructura
*   **Entorno Local:** Windows 10/11.
*   **Producción (Planeado):** VPS único gestionado con Coolify (Docker).

## 3. Estructura de Módulos (Apps)

El proyecto se organiza en aplicaciones Django desacopladas por dominio de negocio:

### A. `core` (Núcleo)
Contiene la lógica transversal y los modelos base.
*   **Modelos:** `Venta`, `BoletoImportado`, `Pago`.
*   **Servicios:**
    *   `ticket_parser.py`: El "cerebro" que lee PDFs/Emails.
    *   `venta_automation.py`: Orquesta la creación automática de ventas y cálculo de comisiones.
    *   `facturacion_service.py`: Genera facturas fiscales y PDFs.

### B. `cotizaciones` (Comercial)
Gestión de propuestas previas a la venta.
*   **Funcionalidad:** Dashboard de cotizaciones, ciclo de vida (Borrador -> Aceptada).
*   **Integración:** Futura conversión automática a Venta.

### C. `contabilidad` (Financiero)
Motor contable invisible.
*   **Normativa:** VEN-NIF (Venezuela).
*   **Automatización:** Genera asientos contables automáticos (Debe/Haber) al facturar o cobrar, calculando diferenciales cambiarios e impuestos (IVA/IGTF).
*   **Modelos:** `AsientoContable`, `Movimiento`, `Cuenta` (Plan de Cuentas).

### D. `personas` (CRM)
Gestión de actores del sistema.
*   **Modelos:** `Cliente`, `Pasajero`, `UsuarioAgencia`.

## 4. Flujos de Datos Críticos

### Flujo 1: Automatización de Boletos (El "Wow Factor")
1.  **Recepción:** Email con boleto llega a `boletotravelinkeo@gmail.com`.
2.  **Detección:** Celery (`process_incoming_emails`) descarga el adjunto.
3.  **Extracción:** `KIUParser` (u otros) extrae PNR, Pasajero y **Datos Financieros** (Base, IVA YN, Total).
4.  **Procesamiento:** `VentaAutomationService` calcula la comisión de la agencia (según `AerolineaConfig`) y crea la `Venta` en BD.
5.  **Resultado:** El agente ve la venta lista en su Dashboard sin haber tecleado nada.

### Flujo 2: Ciclo Contable Automático
1.  **Venta/Factura:** Al emitir factura, se genera asiento de Cuentas por Cobrar vs Ingresos/Pasivos.
2.  **Cobranza:** Al registrar pago en USD, se baja la CxC a tasa histórica.
3.  **Diferencial:** El sistema compara Tasa del Día vs Tasa Factura.
    *   Si hay ganancia cambiaria -> Genera Nota de Débito por el IVA de esa ganancia (Fiscal).

## 5. Mapa de Carpetas Clave
```text
travelhub_project/
├── core/
│   ├── models/          # Modelos divididos por archivo (ventas.py, boletos.py...)
│   ├── services/        # Lógica de negocio pura (no vistas)
│   ├── parsers/         # Motores de extracción (kiu_parser.py, sabre_parser.py)
│   ├── templates/       # HTML (Jinja2)
│   └── tasks.py         # Tareas Celery
├── cotizaciones/        # App de propuestas
├── contabilidad/        # App financiera
├── personas/            # App de clientes
├── static/              # Assets (CSS, JS, Img)
├── media/               # Archivos subidos (PDFs, Boletos)
└── manage.py
```

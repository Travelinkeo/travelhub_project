# Arquitectura de TravelHub SaaS

## 1. Multi-Tenancy (Aislamiento de Datos)
TravelHub utiliza una arquitectura de **Shared Database, Shared Schema** con filtrado por fila.

### Implementación:
- Cada modelo principal (Venta, Cliente, Proveedor, Gasto, etc.) posee una clave foránea a un modelo `Agencia`.
- El aislamiento se garantiza mediante un **Middleware** (`core.middleware_saas.AgenciaMiddleware`) que identifica la agencia activa (por dominio o sesión) y un **Mixin/Manager** que filtra automáticamente todas las consultas (`objects.filter(agencia=current_agencia)`).

### Seguridad:
- No se permiten consultas globales sin especificar la agencia.
- Los archivos subidos (PDFs, imágenes) se almacenan en rutas prefijadas con el ID de la agencia en Cloudinary/R2.

## 2. Motor de Automatización (Robot de Boletos)
El núcleo del sistema es un pipeline de procesamiento asíncrono:
1. **Entrada:** Correo electrónico (via Postmark/Resend) o subida manual de PDF/Texto.
2. **Cola:** Tarea de Celery que recibe el contenido.
3. **Parser:** `core.services.ticket_parser_service.py` utiliza una lógica híbrida:
   - **IA (Gemini):** Intenta extraer el JSON estructurado del contenido.
   - **Regex (Fallback):** Si la IA falla o no hay confianza, se aplican reglas deterministas para GDS (Sabre, KIU, Amadeus).
4. **Persistencia:** Normalización de datos y creación de registros en `Venta` e `ItemVenta`.

## 3. Integraciones AI
- **Gemini Pro:** Extracción de datos de boletos, generación de descripciones de ventas y asistente de contabilidad.
- **Magic Quoter:** Generación automática de cotizaciones a partir de lenguaje natural.

## 4. Infraestructura
- **Backend:** Django 5.x.
- **Frontend:** HTMX + Alpine.js (SPA feel sin complejidad de React).
- **Base de Datos:** PostgreSQL 17.
- **Background Tasks:** Celery + Redis.
- **Emails:** Resend / Postmark.
- **WhatsApp:** Evolution API / WAHA.

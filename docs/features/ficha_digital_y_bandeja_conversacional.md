# Ficha Digital Interactiva del Viajero y Bandeja Conversacional por Expediente

## 📌 Descripción General
TravelHub Pro incorpora un ecosistema unificado de cara al cliente y al agente para la gestión de itinerarios y comunicación en tiempo real:
1. **Ficha Digital Interactiva del Pasajero (Web Live Portal):** Portal web responsive sin login tradicional, protegido mediante tokens criptográficos de 30 días, con sincronización nativa a calendarios y cuenta regresiva de despegue.
2. **Bandeja Conversacional por Expediente (Agent Hub):** Panel reactivo en el detalle de la venta (`VentaDetailView`) que centraliza el historial de mensajes por Email (RFC 2822) y WhatsApp con refresco pasivo vía HTMX y encolamiento asíncrono con Celery.

---

## 🏛️ Arquitectura y Modelos

### 1. Modelo de Datos (`apps/bookings/models/comunicacion.py`)
- **`VentaMensaje`**:
  - `venta`: Venta asociada (`ForeignKey(Venta, related_name="mensajes_comunicacion")`).
  - `direccion`: `IN` (Entrante del cliente) o `OUT` (Saliente del agente).
  - `canal`: `EMAIL` o `WHATSAPP`.
  - `message_id` & `in_reply_to`: Cabeceras RFC 2822 para threading de correos en Gmail/Outlook.
  - `cuerpo`: Texto del mensaje.
  - `enlace_ficha_digital`: URL firmada del itinerario inyectada en el mensaje.
- **`MensajeAdjunto`**:
  - `archivo`: Archivo adjunto (PDF de boleto generado, comprobantes).
  - `nombre_original`: Nombre descriptivo del archivo.

---

## 🔐 Seguridad y Tokens Criptográficos

### `ItineraryCryptoService` (`apps/bookings/services/itinerary_service.py`)
- Utiliza `django.core.signing.TimestampSigner` con salt `travelhub.itinerary.v1`.
- Genera enlaces seguros con expiración automática de 30 días:
  ```text
  https://travelhub.cc/itinerary/v1/live/<token>/
  ```
- Desempaqueta y valida en tiempo constante el par `(venta_id, agencia_id)` garantizando aislamiento multi-inquilino.

---

## 📅 Sincronización con Calendarios (`.ics`)
- **Endpoint:** `/itinerary/v1/live/<token>/calendar.ics`
- **Protocolo:** RFC 5545 iCalendar (`text/calendar; charset=utf-8`).
- **Compatibilidad:** 1-clic en Google Calendar, Apple Calendar (iOS/macOS), Microsoft Outlook.
- Genera eventos `VEVENT` detallados para cada `SegmentoVuelo` (con IATA, aerolínea, horarios y equipaje) y `AlojamientoReserva` (check-in, check-out y régimen).

---

## 🚀 Despacho Asíncrono (`dispatch_booking_message_task`)
- Tarea Celery en `apps/bookings/tasks.py` con backoff exponencial.
- **Email:**
  - Inyecta cabeceras `Message-ID`, `In-Reply-To` y `References`.
  - Adjunta el PDF oficial del boleto si `attach_ticket=True`.
- **WhatsApp:**
  - Despacha mediante la integración unificada de `WhatsAppService` / Evolution API.

---

## 🖥️ Componentes Frontend y Vistas
| Vista / Parcial | Ruta | Propósito |
|---|---|---|
| `itinerary_live_page.html` | `/itinerary/v1/live/<token>/` | Ficha interactiva pública para el pasajero con cuenta regresiva. |
| `itinerary_live_timeline.html` | Parcial | Cronograma de vuelos estilo tarjeta de embarque, hoteles y traslados. |
| `comunicacion_chat_panel.html` | Parcial | Panel lateral conversacional en el detalle de la venta. |
| `_message_list.html` & `_single_message.html` | Parcial HTMX | Streaming de burbujas de chat con polling cada 15 segundos. |
| `generate_ical_calendar` | `/itinerary/v1/live/<token>/calendar.ics` | Descarga directa del calendario en formato `.ics`. |

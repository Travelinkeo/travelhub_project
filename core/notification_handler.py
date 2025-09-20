
import logging
from typing import Any

from core.gemini import generate_content

# Asumimos que los modelos y la función de Gemini están disponibles
from core.models.personas import Cliente
from core.models.ventas import Venta

# --- Simulación de Servicios Externos ---

def enviar_whatsapp(numero_cliente: str, mensaje: str):
    """
    Función simulada para enviar un mensaje de WhatsApp.
    """
    logging.info("--- SIMULACIÓN DE ENVÍO DE WHATSAPP ---")
    logging.info(f"Destinatario: {numero_cliente}")
    logging.info(f"Mensaje: {mensaje}")
    logging.info("--- FIN SIMULACIÓN ---")
    return True

def get_calendar_service() -> Any | None:
    """
    Simulación de la obtención del servicio de Google Calendar.
    En una implementación real, se adaptaría la función 'get_gmail_service'.
    """
    logging.info("Simulando la obtención del servicio de Google Calendar...")
    return True # Devolvemos un valor verdadero para la simulación.

# --- Lógica Principal del Manejador ---

def generate_whatsapp_notification(cliente: Cliente, datos_cambio: dict[str, Any]) -> str:
    """
    Usa Gemini para redactar un mensaje de WhatsApp claro y tranquilizador.
    """
    logging.info(f"Generando mensaje de WhatsApp para {cliente.get_nombre_completo()}")
    
    pnr = datos_cambio.get("pnr", "N/A")
    aerolinea = datos_cambio.get("aerolinea", "N/A")
    vuelo_antiguo = datos_cambio.get("vuelo_antiguo", {})
    vuelo_nuevo = datos_cambio.get("vuelo_nuevo", {})

    prompt = f"""
    Actúa como un asistente de viajes proactivo y empático de la agencia TravelHub.
    Tu tarea es redactar un mensaje de WhatsApp para notificar a un cliente sobre un cambio urgente en su itinerario de vuelo.
    El tono debe ser tranquilizador, claro y profesional.

    **Contexto:**
    - **Nombre del Cliente:** {cliente.get_nombre_completo()}
    - **Código de Reserva (PNR):** {pnr}
    - **Aerolínea:** {aerolinea}

    **Detalles del Cambio:**
    - **Vuelo Original:**
        - Fecha: {vuelo_antiguo.get('fecha', 'N/A')}
        - Hora de Salida: {vuelo_antiguo.get('hora_salida', 'N/A')}
    - **NUEVO Vuelo:**
        - Fecha: {vuelo_nuevo.get('fecha', 'N/A')}
        - Hora de Salida: {vuelo_nuevo.get('hora_salida', 'N/A')}

    **Instrucciones para el Mensaje:**
    1. Saluda al cliente por su nombre.
    2. Identifícate como un asistente de TravelHub.
    3. Informa sobre el cambio de horario en su vuelo, mencionando el PNR.
    4. Presenta claramente la información del vuelo original y del nuevo vuelo.
    5. Asegúrale al cliente que su reserva está confirmada.
    6. Menciona que su calendario ha sido actualizado automáticamente.
    7. Ofrécele ayuda para cualquier duda.
    
    Genera únicamente el texto del mensaje de WhatsApp.
    """
    
    return generate_content(prompt)


def handle_urgent_notification(extracted_data: dict[str, Any]):
    """
    Orquesta el proceso de manejo de una notificación urgente.
    """
    pnr = extracted_data.get("pnr") or extracted_data.get("codigo_reserva")
    if not pnr:
        logging.error("No se encontró PNR o código de reserva en los datos extraídos.")
        return

    logging.info(f"Manejando notificación urgente para la reserva PNR: {pnr}")

    try:
        venta = Venta.objects.select_related('cliente').get(localizador=pnr)
        cliente = venta.cliente
        logging.info(f"Venta y cliente ({cliente.get_nombre_completo()}) encontrados.")
    except Venta.DoesNotExist:
        logging.error(f"No se encontró una venta con el PNR {pnr}.")
        return
    except Exception as e:
        logging.error(f"Error buscando la venta {pnr}: {e}")
        return

    if venta.google_calendar_event_id:
        calendar_service = get_calendar_service()
        if calendar_service:
            try:
                logging.info(f"SIMULACIÓN: Se actualizaría el evento de calendario {venta.google_calendar_event_id}.")
            except Exception as e:
                logging.error(f"No se pudo actualizar el evento del calendario: {e}")
    
    mensaje_notificacion = generate_whatsapp_notification(cliente, extracted_data)

    if cliente.telefono_principal:
        enviar_whatsapp(cliente.telefono_principal, mensaje_notificacion)
    else:
        logging.warning(f"El cliente {cliente.get_nombre_completo()} no tiene un teléfono para notificar.")

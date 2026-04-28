
import logging
from typing import Any

from core.gemini import generate_content

logger = logging.getLogger(__name__)

def generate_whatsapp_message_for_document(document_type: str, client_name: str, data: dict[str, Any]) -> str:
    """
    Llama a Gemini para generar un mensaje de WhatsApp amigable para enviar un documento.

    Args:
        document_type: El tipo de documento (ej: "Factura", "Boleto de Avión", "Cotización").
        client_name: El nombre del cliente.
        data: Un diccionario con datos relevantes del documento (ej: monto, localizador).

    Returns:
        Un string con el mensaje redactado.
    """
    prompt = f"""
    Eres el asistente virtual de la agencia de viajes TravelHub.
    Tu tarea es redactar un mensaje corto, amigable y profesional para enviar un documento a un cliente por WhatsApp.

    **Instrucciones:**
    - Saluda al cliente por su nombre.
    - Menciona qué documento se le está enviando.
    - Si hay un monto o un localizador, menciónalo de forma clara.
    - Mantén un tono cercano y servicial.
    - No añadas placeholders como [Nombre del Cliente], usa el nombre directamente.
    - Tu respuesta debe ser únicamente el texto del mensaje, sin comillas ni texto adicional.

    **Datos para el Mensaje:**
    - **Cliente:** {client_name}
    - **Tipo de Documento:** {document_type}
    - **Detalles Adicionales:** {data}

    **Ejemplo para una factura:**
    Hola {client_name}, ¡espero que estés muy bien! Te adjunto la factura de tu reciente compra por un total de {data.get('total', '...')}. ¡Gracias por confiar en TravelHub! ✈️

    **Ejemplo para un boleto:**
    ¡Hola {client_name}! La aventura te espera. ✨ Te envío tu boleto de avión con localizador {data.get('localizador', '...')}. ¡Que tengas un viaje increíble!
    """
    try:
        message = generate_content(prompt)
        return message.strip()
    except Exception as e:
        logger.error(f"Error al generar mensaje de WhatsApp con Gemini: {e}")
        return f"Hola {client_name}, te adjuntamos tu {document_type}."

def send_whatsapp_with_attachment(client_number: str, message: str, pdf_url: str):
    """
    Envía un mensaje de WhatsApp con un archivo adjunto usando un proveedor de API.

    NOTA: Esta es una función simulada. La implementación real dependerá del proveedor
    de la API de WhatsApp (ej: Twilio, Meta API, etc.).

    Args:
        client_number: El número de teléfono del cliente en formato internacional (ej: +521123456789).
        message: El texto del mensaje a enviar.
        pdf_url: La URL pública y accesible del PDF a adjuntar.
    """
    # --- IMPLEMENTACIÓN REAL AQUÍ ---
    # Aquí iría el código que llama a la API de WhatsApp.
    # Ejemplo con una API hipotética:
    #
    # from some_whatsapp_provider import WhatsAppClient
    #
    # client = WhatsAppClient(api_key=settings.WHATSAPP_API_KEY, api_secret=settings.WHATSAPP_API_SECRET)
    # try:
    #     response = client.messages.create(
    #         to=f"whatsapp:{client_number}",
    #         from_=f"whatsapp:{settings.WHATSAPP_SENDER_NUMBER}",
    #         body=message,
    #         media_url=[pdf_url]
    #     )
    #     logger.info(f"Mensaje de WhatsApp enviado a {client_number}. SID: {response.sid}")
    #     return {"success": True, "sid": response.sid}
    # except Exception as e:
    #     logger.error(f"Error al enviar WhatsApp a {client_number}: {e}")
    #     return {"success": False, "error": str(e)}
    #
    # --- FIN DE IMPLEMENTACIÓN REAL ---

    # Simulación para propósitos de desarrollo
    logger.info("--- SIMULACIÓN DE ENVÍO DE WHATSAPP ---")
    logger.info(f"Destinatario: {client_number}")
    logger.info(f"Mensaje: {message}")
    logger.info(f"Adjunto: {pdf_url}")
    logger.info("--- FIN DE SIMULACIÓN ---")
    return {"success": True, "sid": "simulated_message_id_12345"}


import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)

def enviar_mensaje_meta_api(numero_cliente, mensaje, agencia=None):
    """
    Servicio para enviar mensajes a través de la WhatsApp Cloud API (Meta).
    Implementación base para el Sistema de Notificaciones Resiliente.
    """
    try:
        # SaaS Logic: Prioritize Agency Config
        token = settings.WHATSAPP_TOKEN
        phone_id = settings.WHATSAPP_PHONE_ID
        
        if agencia and agencia.configuracion_api.get('WHATSAPP_TOKEN'):
            token = agencia.configuracion_api.get('WHATSAPP_TOKEN')
            phone_id = agencia.configuracion_api.get('WHATSAPP_PHONE_ID')

        if not token or not phone_id:
            logger.error("WhatsApp Config Missing (Token or Phone ID)")
            return {'success': False, 'error_message': 'Configuración de WhatsApp faltante'}

        url = f"https://graph.facebook.com/v18.0/{phone_id}/messages"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        # Limpiar número (solo dígitos, incluir código de país si no está)
        clean_number = "".join(filter(str.isdigit, str(numero_cliente)))
        
        # Payload para mensaje de texto simple (se puede extender a plantillas)
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": clean_number,
            "type": "text",
            "text": {"body": mensaje}
        }

        logger.info(f"Enviando WhatsApp a {clean_number} vía Meta API...")
        response = requests.post(url, json=payload, headers=headers, timeout=20)
        
        if response.status_code in [200, 201]:
            logger.info(f"✅ WhatsApp enviado a {clean_number}. ID: {response.json().get('messages', [{}])[0].get('id')}")
            return {'success': True, 'data': response.json()}
        else:
            error_data = response.json().get('error', {})
            error_msg = error_data.get('message', 'Unknown Meta Error')
            logger.error(f"❌ Error Meta API ({response.status_code}): {error_msg}")
            return {'success': False, 'error_message': error_msg}

    except Exception as e:
        logger.exception(f"Excepción enviando mensaje WhatsApp: {str(e)}")
        return {'success': False, 'error_message': str(e)}

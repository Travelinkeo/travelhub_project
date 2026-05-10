import logging
import requests
from django.conf import settings
from .evolution_api_service import EvolutionService

logger = logging.getLogger(__name__)

def enviar_mensaje_meta_api(numero_cliente, mensaje, agencia=None):
    """
    Servicio para enviar mensajes a través de la WhatsApp Cloud API (Meta).
    Mantenido como fallback para mensajes de texto.
    """
    try:
        # SaaS Logic: Prioritize Agency Config
        token = settings.WHATSAPP_TOKEN
        phone_id = settings.WHATSAPP_PHONE_ID
        
        if agencia and agencia.configuracion_api:
            token = agencia.configuracion_api.get('WHATSAPP_TOKEN', token)
            phone_id = agencia.configuracion_api.get('WHATSAPP_PHONE_ID', phone_id)

        if not token or not phone_id:
            logger.error("WhatsApp Meta Config Missing")
            return {'success': False, 'error_message': 'Configuración de Meta faltante'}

        url = f"https://graph.facebook.com/v18.0/{phone_id}/messages"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        clean_number = "".join(filter(str.isdigit, str(numero_cliente)))
        
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": clean_number,
            "type": "text",
            "text": {"body": mensaje}
        }

        response = requests.post(url, json=payload, headers=headers, timeout=20)
        
        if response.status_code in [200, 201]:
            return {'success': True, 'provider': 'meta', 'data': response.json()}
        else:
            return {'success': False, 'error_message': response.text}

    except Exception as e:
        logger.exception(f"Error en Meta API: {str(e)}")
        return {'success': False, 'error_message': str(e)}

def send_whatsapp_message(number, text, agencia=None, media_url=None, file_name=None):
    """
    PUNTO DE ENTRADA UNIFICADO (Fase B).
    Decide inteligentemente qué proveedor usar.
    """
    # 1. Determinar nombre de instancia (Multi-tenant)
    instance_name = "default"
    if agencia and agencia.subdominio_slug:
        instance_name = agencia.subdominio_slug

    # 2. Intentar vía EVOLUTION API (Soporta Media)
    try:
        success = False
        if media_url:
            success = EvolutionService.send_media(
                instance_name, number, media_url, caption=text, file_name=file_name
            )
        else:
            success = EvolutionService.send_text(instance_name, number, text)

        if success:
            return {'success': True, 'provider': 'evolution'}
    except Exception as e:
        logger.warning(f"⚠️ Evolution API falló para {number}: {e}")

    # 3. FALLBACK A META (Solo si es texto)
    if not media_url:
        logger.info(f"🔄 Reintentando vía Meta API para {number}...")
        return enviar_mensaje_meta_api(number, text, agencia=agencia)

    return {
        'success': False, 
        'error_message': 'No se pudo enviar el mensaje por ningún proveedor (Evolution/Meta)'
    }

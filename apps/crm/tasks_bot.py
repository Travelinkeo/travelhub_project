import logging
from celery import shared_task
from apps.crm.services.whatsapp_bot_service import procesar_mensaje_entrante

logger = logging.getLogger(__name__)

@shared_task(bind=True, queue='ia_fast', max_retries=5)
def whatsapp_ai_task(self, telefono_cliente, nombre_perfil, mensaje_texto):
    """
    Despacha el mensaje de WhatsApp a Gemini con resiliencia ante caídas temporales.
    """
    try:
        logger.info(f"AI Task: Procesando mensaje de {telefono_cliente}")
        return procesar_mensaje_entrante(telefono_cliente, nombre_perfil, mensaje_texto)
    except Exception as e:
        logger.error(f"FALLO DE RESILIENCIA: Error procesando WhatsApp ({telefono_cliente}): {str(e)}")
        # Reintento proactivo tras 60 segundos por si hay caída de API Gemini
        raise self.retry(exc=e, countdown=60)

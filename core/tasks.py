"""Tareas asíncronas de Celery"""
from celery import shared_task
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def process_ticket_async(self, file_path):
    """
    Procesa un boleto de forma asíncrona.
    
    Args:
        file_path: Ruta al archivo del boleto
        
    Returns:
        dict con datos parseados
    """
    try:
        from core.services.ticket_parser_service import orquestar_parseo_de_boleto
        
        with open(file_path, 'rb') as f:
            datos, mensaje = orquestar_parseo_de_boleto(f)
        
        if datos:
            logger.info(f"✅ Boleto procesado: {file_path}")
            return {'success': True, 'data': datos}
        else:
            logger.error(f"❌ Error procesando boleto: {mensaje}")
            return {'success': False, 'error': mensaje}
    
    except Exception as e:
        logger.exception(f"Error en process_ticket_async: {e}")
        # Reintentar hasta 3 veces
        raise self.retry(exc=e, countdown=60)


@shared_task
def generate_pdf_async(data):
    """
    Genera PDF de boleto de forma asíncrona.
    
    Args:
        data: Datos parseados del boleto
        
    Returns:
        str con nombre del archivo generado
    """
    try:
        from core.ticket_parser import generate_ticket
        
        pdf_bytes, filename = generate_ticket(data)
        
        # Guardar PDF
        from django.conf import settings
        import os
        
        media_dir = os.path.join(settings.MEDIA_ROOT, 'boletos_generados')
        os.makedirs(media_dir, exist_ok=True)
        
        file_path = os.path.join(media_dir, filename)
        with open(file_path, 'wb') as f:
            f.write(pdf_bytes)
        
        logger.info(f"✅ PDF generado: {filename}")
        return filename
    
    except Exception as e:
        logger.exception(f"Error generando PDF: {e}")
        return None


@shared_task
def send_notification_async(event, recipient, data):
    """
    Envía notificación de forma asíncrona.
    
    Args:
        event: Tipo de evento
        recipient: Dict con email y teléfono
        data: Datos para el mensaje
    """
    try:
        from core.notifications import notification_service
        
        results = notification_service.notify(event, recipient, data)
        logger.info(f"✅ Notificación enviada: {event} - {results}")
        return results
    
    except Exception as e:
        logger.exception(f"Error enviando notificación: {e}")
        return {'error': str(e)}


@shared_task
def warmup_cache_task():
    """Tarea programada para calentar caché"""
    from django.core.management import call_command
    call_command('warmup_cache')
    logger.info("✅ Caché calentado por tarea programada")

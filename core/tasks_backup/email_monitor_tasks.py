"""
Tareas Celery para monitoreo automático de correos de boletos
"""
import logging
from celery import shared_task
from core.services.email_monitor_service import EmailMonitorService

logger = logging.getLogger(__name__)


@shared_task(name='core.monitor_boletos_email')
def monitor_boletos_email():
    """
    Monitorea boletotravelinkeo@gmail.com cada 5 minutos
    Envía PDF a travelinkeo@gmail.com
    """
    try:
        logger.info("🔍 Monitoreando correos de boletos...")
        
        monitor = EmailMonitorService(
            notification_type='email',
            destination='travelinkeo@gmail.com',
            mark_as_read=True,
            process_all=False,
            force_reprocess=False
        )
        
        procesados = monitor.procesar_una_vez()
        
        if procesados > 0:
            logger.info(f"✅ {procesados} boletos procesados")
        
        return {'success': True, 'procesados': procesados}
        
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        return {'success': False, 'error': str(e)}


@shared_task(name='core.monitor_boletos_whatsapp')
def monitor_boletos_whatsapp():
    """
    Fase 2: Notificación WhatsApp a +584126080861
    """
    try:
        monitor = EmailMonitorService(
            notification_type='whatsapp',
            destination='+584126080861',
            mark_as_read=True,
            process_all=False
        )
        
        procesados = monitor.procesar_una_vez()
        return {'success': True, 'procesados': procesados}
        
    except Exception as e:
        logger.error(f"❌ Error WhatsApp: {e}")
        return {'success': False, 'error': str(e)}

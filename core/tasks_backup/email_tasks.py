import logging
from celery import shared_task
from django.utils import timezone
from core.models import Agencia
from core.services.email_monitor_service import EmailMonitorService

logger = logging.getLogger(__name__)

@shared_task
def check_agencies_emails():
    """
    Tarea programada (Celery/Beat) para revisar correos de todas las agencias activas.
    Itera sobre cada agencia configurada y ejecuta el monitoreo.
    """
    agencias = Agencia.objects.filter(activa=True, email_monitor_active=True)
    
    if not agencias.exists():
        logger.info("📭 No hay agencias con monitoreo de correo activo.")
        return "No active agencies"

    logger.info(f"🚀 Iniciando monitoreo de correo para {agencias.count()} agencias...")
    count_processed = 0
    
    for agencia in agencias:
        try:
            # Validar credenciales mínimas antes de instanciar
            if not agencia.email_monitor_user or not agencia.email_monitor_password:
                logger.warning(f"⚠️ Agencia {agencia.nombre} marcada activa pero sin credenciales.")
                continue

            logger.info(f"🔍 Revisando buzón de: {agencia.nombre} ({agencia.email_monitor_user})")
            
            # Instanciar servicio solo para esta agencia
            monitor = EmailMonitorService(
                agencia=agencia,
                notification_type='whatsapp', # Default, puede venir de config
                process_all=False,            # Solo nuevos (UNSEEN)
                mark_as_read=True             # Marcar como leído tras procesar
            )
            
            # Ejecutar proceso único (no bucle while)
            processed = monitor.procesar_una_vez()
            count_processed += processed
            
            # Actualizar timestamp
            agencia.email_monitor_last_check = timezone.now()
            agencia.save(update_fields=['email_monitor_last_check'])
            
        except Exception as e:
            logger.error(f"❌ Error monitoreando agencia {agencia.nombre}: {e}", exc_info=True)
            # Continuar con la siguiente agencia, no detener el loop
            continue

    return f"Completed. {count_processed} emails processed across {agencias.count()} agencies."

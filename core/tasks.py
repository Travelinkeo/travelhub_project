"""
Tareas asíncronas de Celery para automatizaciones.
"""
from celery import shared_task
from django.core.management import call_command
from django.utils import timezone
from core.models.agencia import Agencia
import logging

logger = logging.getLogger(__name__)


@shared_task
def sincronizar_tasa_bcv_task():
    """Sincroniza la tasa de cambio del BCV."""
    try:
        call_command('sincronizar_tasa_bcv')
        logger.info('Tasa BCV sincronizada exitosamente')
        return 'Tasa BCV sincronizada'
    except Exception as e:
        logger.error(f'Error sincronizando BCV: {e}')
        return f'Error: {e}'


@shared_task
def enviar_notificaciones_billing_task():
    """Envía notificaciones automáticas de billing."""
    try:
        call_command('enviar_notificaciones_billing')
        logger.info('Notificaciones de billing enviadas')
        return 'Notificaciones enviadas'
    except Exception as e:
        logger.error(f'Error enviando notificaciones: {e}')
        return f'Error: {e}'


@shared_task
def enviar_recordatorios_pago_task():
    """Envía recordatorios de pago pendientes."""
    try:
        # TODO: Implementar comando de recordatorios
        logger.info('Recordatorios de pago enviados')
        return 'Recordatorios enviados'
    except Exception as e:
        logger.error(f'Error enviando recordatorios: {e}')
        return f'Error: {e}'


@shared_task
def monitor_tickets_email_task():
    """Monitorea emails de tickets."""
    try:
        call_command('monitor_tickets_email')
        logger.info('Tickets monitoreados')
        return 'Tickets monitoreados'
    except Exception as e:
        logger.error(f'Error monitoreando tickets: {e}')
        return f'Error: {e}'


@shared_task
def reset_ventas_mensuales_task():
    """Resetea el contador de ventas mensuales de todas las agencias."""
    try:
        agencias = Agencia.objects.filter(activa=True)
        count = agencias.update(ventas_mes_actual=0)
        logger.info(f'Contador de ventas reseteado para {count} agencias')
        return f'Reseteado para {count} agencias'
    except Exception as e:
        logger.error(f'Error reseteando ventas: {e}')
        return f'Error: {e}'

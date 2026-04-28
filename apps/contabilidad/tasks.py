"""
Tareas asíncronas de Celery para contabilidad.
"""
from celery import shared_task
from django.core.management import call_command
import logging

logger = logging.getLogger(__name__)


@shared_task
def cierre_mensual_task():
    """Ejecuta el cierre contable mensual."""
    try:
        call_command('cierre_mensual')
        logger.info('Cierre mensual ejecutado exitosamente')
        return 'Cierre mensual completado'
    except Exception as e:
        logger.error(f'Error en cierre mensual: {e}')
        return f'Error: {e}'

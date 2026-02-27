# Tareas Celery
from .email_monitor_tasks import monitor_boletos_email, monitor_boletos_whatsapp

__all__ = ['monitor_boletos_email', 'monitor_boletos_whatsapp']

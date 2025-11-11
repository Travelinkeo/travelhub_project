"""
Configuración de tareas programadas con Celery Beat.
Reemplaza los scripts .bat en producción.
"""
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    # Sincronizar tasa BCV diariamente a las 9 AM
    'sincronizar-bcv-diario': {
        'task': 'core.tasks.sincronizar_tasa_bcv_task',
        'schedule': crontab(hour=9, minute=0),  # 9:00 AM todos los días
    },
    
    # Enviar notificaciones de billing diariamente a las 8 AM
    'notificaciones-billing-diario': {
        'task': 'core.tasks.enviar_notificaciones_billing_task',
        'schedule': crontab(hour=8, minute=0),  # 8:00 AM todos los días
    },
    
    # Enviar recordatorios de pago diariamente a las 10 AM
    'recordatorios-pago-diario': {
        'task': 'core.tasks.enviar_recordatorios_pago_task',
        'schedule': crontab(hour=10, minute=0),  # 10:00 AM todos los días
    },
    
    # Cierre mensual el día 1 de cada mes a las 2 AM
    'cierre-mensual': {
        'task': 'contabilidad.tasks.cierre_mensual_task',
        'schedule': crontab(hour=2, minute=0, day_of_month=1),  # 2:00 AM del día 1
    },
    
    # Monitorear tickets de email cada 15 minutos
    'monitor-tickets-email': {
        'task': 'core.tasks.monitor_tickets_email_task',
        'schedule': crontab(minute='*/15'),  # Cada 15 minutos
    },
    
    # Resetear contador de ventas mensuales el día 1 de cada mes
    'reset-ventas-mensuales': {
        'task': 'core.tasks.reset_ventas_mensuales_task',
        'schedule': crontab(hour=0, minute=0, day_of_month=1),  # Medianoche del día 1
    },
    
    # Monitorear correos de boletos cada 5 minutos
    'monitor-boletos-email': {
        'task': 'core.monitor_boletos_email',
        'schedule': crontab(minute='*/5'),  # Cada 5 minutos
    },
}

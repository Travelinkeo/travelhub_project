# travelhub/celery_beat_schedule.py
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    'process-incoming-emails-every-5-minutes': {
        'task': 'core.tasks.process_incoming_emails',
        'schedule': crontab(minute='*/5'),  # Ejecutar cada 5 minutos
        'args': (),
        'options': {
            'expires': 300,  # La tarea no debe tardar más de 5 minutos en completarse
        },
    },
    # Aquí se pueden añadir otras tareas programadas en el futuro
}
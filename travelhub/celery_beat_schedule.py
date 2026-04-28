# travelhub/celery_beat_schedule.py
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    'process-incoming-emails-every-2-minutes': {
        'task': 'core.tasks.process_incoming_emails',
        'schedule': crontab(minute='*/2'),  # Ejecutar cada 2 minutos
        'args': (),
    },
    'check-passport-expiry-daily': {
        'task': 'core.tasks.check_passport_expiry',
        'schedule': crontab(hour=9, minute=0),
        'args': (),
    },
    'check-client-birthdays-daily': {
        'task': 'core.tasks.check_client_birthdays',
        'schedule': crontab(hour=10, minute=0),
        'args': (),
    },
    'check-pending-payments-daily': {
        'task': 'core.tasks.check_pending_payments',
        'schedule': crontab(hour=11, minute=0),
        'args': (),
    },
    'sync-bcv-rates-morning': {
        'task': 'core.tasks.sync_bcv_rates',
        'schedule': crontab(hour=9, minute=0),
        'args': (),
    },
    'sync-bcv-rates-afternoon': {
        'task': 'core.tasks.sync_bcv_rates',
        'schedule': crontab(hour=14, minute=0),
        'args': (),
    },
    # Aquí se pueden añadir otras tareas programadas en el futuro
}
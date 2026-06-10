# travelhub/celery_beat_schedule.py
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    "process-incoming-emails-every-2-minutes": {
        "task": "core.tasks.process_incoming_emails",
        "schedule": crontab(minute="*/2"),  # Ejecutar cada 2 minutos
        "args": (),
    },
    "check-passport-expiry-daily": {
        "task": "core.tasks.check_passport_expiry",
        "schedule": crontab(hour=9, minute=0),
        "args": (),
    },
    "check-client-birthdays-daily": {
        "task": "core.tasks.check_client_birthdays",
        "schedule": crontab(hour=10, minute=0),
        "args": (),
    },
    "check-pending-payments-daily": {
        "task": "core.tasks.check_pending_payments",
        "schedule": crontab(hour=11, minute=0),
        "args": (),
    },
    "sync-bcv-rates-morning": {
        "task": "core.tasks.sync_bcv_rates",
        "schedule": crontab(day_of_week="1-5", hour=9, minute=0),  # Lunes a Viernes 9:00 AM
        "args": (),
    },
    "sync-bcv-rates-afternoon": {
        "task": "core.tasks.sync_bcv_rates",
        "schedule": crontab(day_of_week="1-5", hour=13, minute=0),  # Lunes a Viernes 1:00 PM
        "args": (),
    },
    "backup-database-daily": {
        "task": "core.tasks.backup_database_task",
        "schedule": crontab(hour=3, minute=0),
        "args": (),
    },
    "monitorear-tiempos-limite-cada-15-minutos": {
        "task": "apps.bookings.tasks.monitorear_tiempos_limite_periodico_task",
        "schedule": 900.0,  # Cada 15 minutos
        "args": (),
    },
}

# travelhub/celery_beat_schedule.py
from celery.schedules import crontab

QR_CACHE_KEY = "evo_qr:{instance}"
QR_CACHE_TTL = 300  # 5 minutos — suficiente margen antes del refresh automático (90s)

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
    "check-upcoming-flights-daily": {
        "task": "core.tasks.check_upcoming_flights",
        "schedule": crontab(hour=17, minute=0),  # Todos los días 5:00 PM (vuelos del día siguiente)
        "args": (),
    },
    "send-flight-reminders-every-hour": {
        "task": "core.tasks.enviar_recordatorios_vuelo_task",
        "schedule": crontab(minute=0),  # Cada hora
        "args": (),
    },
    "limpiar-axes-mensual": {
        "task": "core.tasks.limpiar_axes_logs",
        "schedule": crontab(day_of_month="1", hour="4", minute="0"),
        "args": (),
    },
    "limpiar-sesiones": {
        "task": "core.tasks.limpiar_sesiones_expiradas",
        "schedule": crontab(hour="3", minute="0"),
        "args": (),
    },
    "limpiar-celery-results": {
        "task": "core.tasks.limpiar_celery_results",
        "schedule": crontab(day_of_week="0", hour="5", minute="0"),
        "kwargs": {"days": 30},
    },
    "reconciliar-contabilidad-diaria": {
        "task": "apps.contabilidad.tasks.ejecutar_reconciliacion_contable",
        "schedule": crontab(hour="1", minute="0"),  # Todos los días a la 1:00 AM
        "args": (),
    },
    "ejecutar-cobranza-ia-diaria": {
        "task": "core.tasks.ejecutar_cobranza_ia_task",
        "schedule": crontab(hour=20, minute=0),  # Todos los días 8:00 PM
        "args": (),
    },
    # Renovar QR de WhatsApp para todas las agencias activas (cada 5 min)
    "refresh-whatsapp-qr-all": {
        "task": "apps.common.tasks.fetch_all_qr_codes_task",
        "schedule": 300.0,  # cada 5 minutos — Evolution API no soporta polling agresivo
        "args": (),
    },
}

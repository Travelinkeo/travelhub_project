# core/tasks.py
# Facade de compatibilidad hacia atrás: re-exporta tareas de sus módulos
# canónicos para que `from core.tasks import X` siga funcionando.
#
# ⚠️  Ya no usa __getattr__: todas las tareas están importadas explícitamente,
#      lo que permite análisis estático, type hints, y que mypy/IDE resuelvan
#      correctamente los símbolos. Si una tarea nueva se añade en apps/*/tasks.py,
#      agrégala AQUÍ como import explícito.
#
# CELERY DESCUBRE TAREAS AUTOMÁTICAMENTE vía app.autodiscover_tasks()
# en travelhub/celery.py. Estas re-exportaciones son SOLO para compatibilidad
# de imports legacy. No afectan el enrutamiento ni la ejecución de tareas.

# ── apps.common.tasks ────────────────────────────────────────────────────────
# ── apps.automation.tasks ────────────────────────────────────────────────────
from apps.automation.tasks import ejecutar_cobranza_ia_task

# ── apps.bookings.tasks ──────────────────────────────────────────────────────
from apps.bookings.tasks import (
    check_upcoming_flights,
    enviar_recordatorios_vuelo_task,
    generar_pdf_ticket_async_task,
    parsear_boleto_individual,
    retry_queued_boletos,
    send_ticket_notification,
)
from apps.common.tasks import (
    answer_telegram_callback_task,
    backup_database_task,
    cleanup_temporary_storage_files,
    create_binance_order_task,
    download_twilio_media_task,
    edit_telegram_message_task,
    enviar_bienvenida_agencia_task,
    enviar_notificacion_whatsapp_task,
    fetch_airline_logo_task,
    fetch_all_qr_codes_task,
    fetch_bcv_rates_task,
    fetch_evolution_qr_task,
    fetch_image_base64_task,
    fetch_tasas_venezuela_task,
    fetch_unsplash_image_task,
    generate_pdf_task,
    get_filename_from_header,
    get_telegram_file_url_task,
    limpiar_axes_logs,
    limpiar_celery_results,
    limpiar_sesiones_expiradas,
    migrar_logos_agencia_task,
    notificar_boleto_procesado_task,
    notificar_confirmacion_pago_task,
    notificar_recordatorio_pago_task,
    notify_migration_alert_task,
    procesar_correo_individual_agencia,
    process_incoming_emails,
    process_twilio_voice_quote_task,
    send_email_task,
    send_evolution_document_task,
    send_evolution_message_task,
    send_factura_to_telegram_task,
    send_telegram_document_task,
    send_telegram_photo_task,
    send_telegram_task,
    send_whatsapp_meta_task,
    send_whatsapp_task,
)

# ── apps.reports.tasks ──────────────────────────────────────────────────────
from apps.reports.tasks import enviar_reportes_programados_task

# ── apps.contabilidad.tasks ──────────────────────────────────────────────────
from apps.contabilidad.tasks import sync_bcv_rates

# ── apps.finance.tasks ───────────────────────────────────────────────────────
from apps.finance.tasks import (
    check_pending_payments,
    create_invoice_from_sale_task,
    procesar_facturacion_masiva_task,
)

# ── Lista completa para inspección programática ──────────────────────────────
__all__ = [
    # apps.common.tasks
    "answer_telegram_callback_task",
    "backup_database_task",
    "cleanup_temporary_storage_files",
    "create_binance_order_task",
    "download_twilio_media_task",
    "edit_telegram_message_task",
    "enviar_bienvenida_agencia_task",
    "enviar_notificacion_whatsapp_task",
    "fetch_airline_logo_task",
    "fetch_all_qr_codes_task",
    "fetch_bcv_rates_task",
    "fetch_evolution_qr_task",
    "fetch_image_base64_task",
    "fetch_tasas_venezuela_task",
    "fetch_unsplash_image_task",
    "generate_pdf_task",
    "get_filename_from_header",
    "get_telegram_file_url_task",
    "limpiar_axes_logs",
    "limpiar_celery_results",
    "limpiar_sesiones_expiradas",
    "migrar_logos_agencia_task",
    "notificar_boleto_procesado_task",
    "notificar_confirmacion_pago_task",
    "notificar_recordatorio_pago_task",
    "notify_migration_alert_task",
    "procesar_correo_individual_agencia",
    "process_incoming_emails",
    "process_twilio_voice_quote_task",
    "send_email_task",
    "send_evolution_document_task",
    "send_evolution_message_task",
    "send_factura_to_telegram_task",
    "send_telegram_document_task",
    "send_telegram_photo_task",
    "send_telegram_task",
    "send_whatsapp_meta_task",
    "send_whatsapp_task",
    # apps.bookings.tasks
    "check_upcoming_flights",
    "enviar_recordatorios_vuelo_task",
    "generar_pdf_ticket_async_task",
    "parsear_boleto_individual",
    "retry_queued_boletos",
    "send_ticket_notification",
    # apps.finance.tasks
    "check_pending_payments",
    "create_invoice_from_sale_task",
    "procesar_facturacion_masiva_task",
    # apps.contabilidad.tasks
    "sync_bcv_rates",
    # apps.reports.tasks
    "enviar_reportes_programados_task",
    # apps.automation.tasks
    "ejecutar_cobranza_ia_task",
]

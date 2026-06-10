# core/tasks.py
# Lazy loading facade for backward compatibility to avoid circular imports.
# NEW TASKS: After adding a task to apps/*/tasks.py, add its name here
# mapped to its canonical module so `from core.tasks import new_task` works.
# Example: 'my_new_task': 'apps.common.tasks',

import importlib

_TASK_MAPPINGS = {
    # apps.common.tasks
    "get_filename_from_header": "apps.common.tasks",
    "procesar_correo_individual_agencia": "apps.common.tasks",
    "process_incoming_emails": "apps.common.tasks",
    "enviar_notificacion_whatsapp_task": "apps.common.tasks",
    "migrar_logos_agencia_task": "apps.common.tasks",
    "cleanup_temporary_storage_files": "apps.common.tasks",
    "backup_database_task": "apps.common.tasks",
    "send_telegram_task": "apps.common.tasks",
    "send_whatsapp_task": "apps.common.tasks",
    "generate_pdf_task": "apps.common.tasks",
    "send_telegram_document_task": "apps.common.tasks",
    "send_telegram_photo_task": "apps.common.tasks",
    "send_factura_to_telegram_task": "apps.common.tasks",
    "create_binance_order_task": "apps.common.tasks",
    "notify_migration_alert_task": "apps.common.tasks",
    "answer_telegram_callback_task": "apps.common.tasks",
    "edit_telegram_message_task": "apps.common.tasks",
    "send_evolution_message_task": "apps.common.tasks",
    "send_evolution_document_task": "apps.common.tasks",
    "fetch_unsplash_image_task": "apps.common.tasks",
    "fetch_airline_logo_task": "apps.common.tasks",
    "download_twilio_media_task": "apps.common.tasks",
    "send_whatsapp_meta_task": "apps.common.tasks",
    "get_telegram_file_url_task": "apps.common.tasks",
    "fetch_bcv_rates_task": "apps.common.tasks",
    "fetch_tasas_venezuela_task": "apps.common.tasks",
    "fetch_image_base64_task": "apps.common.tasks",
    "send_email_task": "apps.common.tasks",
    "enviar_bienvenida_agencia_task": "apps.common.tasks",
    "notificar_confirmacion_pago_task": "apps.common.tasks",
    "notificar_recordatorio_pago_task": "apps.common.tasks",
    "notificar_boleto_procesado_task": "apps.common.tasks",
    "process_twilio_voice_quote_task": "apps.common.tasks",
    "fetch_evolution_qr_task": "apps.common.tasks",
    # apps.bookings.tasks
    "parsear_boleto_individual": "apps.bookings.tasks",
    "retry_queued_boletos": "apps.bookings.tasks",
    "send_ticket_notification": "apps.bookings.tasks",
    "check_upcoming_flights": "apps.bookings.tasks",
    "generar_pdf_ticket_async_task": "apps.bookings.tasks",
    # apps.crm.tasks
    "check_passport_expiry": "apps.crm.tasks",
    "check_client_birthdays": "apps.crm.tasks",
    "task_ocr_passport_fast": "apps.crm.tasks",
    # apps.finance.tasks
    "check_pending_payments": "apps.finance.tasks",
    "procesar_facturacion_masiva_task": "apps.finance.tasks",
    "create_invoice_from_sale_task": "apps.finance.tasks",
    # apps.contabilidad.tasks
    "sync_bcv_rates": "apps.contabilidad.tasks",
}


def __getattr__(name):
    if name in _TASK_MAPPINGS:
        module_path = _TASK_MAPPINGS[name]
        module = importlib.import_module(module_path)
        return getattr(module, name)
    raise AttributeError(f"module {__name__} has no attribute {name}")

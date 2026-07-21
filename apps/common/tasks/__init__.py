# Auto-generated from tasks.py refactor

from .email_tasks import (  # noqa: F403,F405
    _notificar_operador,  # noqa: F401
    _notificar_operador_telegram,  # noqa: F401
    _notificar_operador_whatsapp,  # noqa: F401
    get_filename_from_header,
    migrar_logos_agencia_task,
    notify_migration_alert_task,
    procesar_correo_individual_agencia,
    process_incoming_emails,
    send_email_task,
)
from .evolution import (  # noqa: F403,F405
    fetch_all_qr_codes_task,
    fetch_evolution_qr_task,
    monitor_whatsapp_health_task,
    process_scheduled_whatsapp_messages,
    send_evolution_document_task,
    send_evolution_message_task,
)
from .mantenimiento import (  # noqa: F403,F405
    backup_database_task,
    cleanup_temporary_storage_files,
    limpiar_axes_logs,
    limpiar_celery_results,
    limpiar_sesiones_expiradas,
)
from .notifications import (  # noqa: F403,F405
    enviar_bienvenida_agencia_task,
    notificar_boleto_procesado_task,
    notificar_confirmacion_pago_task,
    notificar_recordatorio_pago_task,
)
from .telegram_tasks import (  # noqa: F403,F405
    answer_telegram_callback_task,
    edit_telegram_message_task,
    get_telegram_file_url_task,
    notify_cliente_alerta_migratoria_task,
    notify_cliente_confirmacion_venta_task,
    notify_cliente_recordatorio_pago_task,
    send_factura_to_telegram_task,
    send_telegram_document_task,
    send_telegram_photo_task,
    send_telegram_task,
    send_telegram_to_client_task,
)
from .utils import (  # noqa: F403,F405
    create_binance_order_task,
    fetch_airline_logo_task,
    fetch_bcv_rates_task,
    fetch_image_base64_task,
    fetch_tasas_venezuela_task,
    fetch_unsplash_image_task,
    generate_pdf_task,
)
from .whatsapp_tasks import (  # noqa: F403,F405
    download_twilio_media_task,
    enviar_notificacion_whatsapp_task,
    process_twilio_voice_quote_task,
    send_factura_to_whatsapp_task,
    send_whatsapp_meta_task,
    send_whatsapp_task,
)

__all__ = [  # noqa: F405
    "get_filename_from_header",
    "procesar_correo_individual_agencia",
    "process_incoming_emails",
    "migrar_logos_agencia_task",
    "send_email_task",
    "notify_migration_alert_task",
    "send_evolution_message_task",
    "send_evolution_document_task",
    "fetch_all_qr_codes_task",
    "fetch_evolution_qr_task",
    "process_scheduled_whatsapp_messages",
    "monitor_whatsapp_health_task",
    "cleanup_temporary_storage_files",
    "backup_database_task",
    "limpiar_axes_logs",
    "limpiar_sesiones_expiradas",
    "limpiar_celery_results",
    "enviar_bienvenida_agencia_task",
    "notificar_confirmacion_pago_task",
    "notificar_recordatorio_pago_task",
    "notificar_boleto_procesado_task",
    "send_telegram_task",
    "send_telegram_document_task",
    "send_telegram_photo_task",
    "send_factura_to_telegram_task",
    "answer_telegram_callback_task",
    "edit_telegram_message_task",
    "get_telegram_file_url_task",
    "send_telegram_to_client_task",
    "notify_cliente_confirmacion_venta_task",
    "notify_cliente_recordatorio_pago_task",
    "notify_cliente_alerta_migratoria_task",
    "generate_pdf_task",
    "create_binance_order_task",
    "fetch_unsplash_image_task",
    "fetch_airline_logo_task",
    "fetch_bcv_rates_task",
    "fetch_tasas_venezuela_task",
    "fetch_image_base64_task",
    "enviar_notificacion_whatsapp_task",
    "send_whatsapp_task",
    "send_factura_to_whatsapp_task",
    "download_twilio_media_task",
    "send_whatsapp_meta_task",
    "process_twilio_voice_quote_task",
]

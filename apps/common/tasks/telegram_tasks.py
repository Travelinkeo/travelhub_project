"""Tareas asíncronas (Celery) para la aplicación common.
"""

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    queue="notifications",
    max_retries=3,
    default_retry_delay=10,
    time_limit=60,
    soft_time_limit=50,
)
def send_telegram_task(self, message, chat_id=None, parse_mode="HTML", agencia_id=None):
    # send_telegram_task: Envía  telegram task. Args: datos del mensaje. Returns: resultado del envío.
    from apps.communications.services.telegram_unified import TelegramNotificationService

    try:
        agencia = None
        if agencia_id:
            from core.models.agencia import Agencia

            agencia = Agencia.objects.get(pk=agencia_id)
        success = TelegramNotificationService.send_message(
            message, chat_id=chat_id, parse_mode=parse_mode, agencia=agencia
        )
        if success:
            logger.info(f"Telegram notification sent (chat={chat_id or 'default'})")
        else:
            logger.warning(f"Telegram notification failed (chat={chat_id or 'default'})")
        return success
    except Exception as exc:
        logger.error(f"Telegram task error: {exc}")
        self.retry(exc=exc)


@shared_task(
    bind=True,
    queue="notifications",
    max_retries=3,
    default_retry_delay=30,
    time_limit=120,
    soft_time_limit=100,
)
def send_telegram_document_task(self, file_path, caption=None, chat_id=None, agencia_id=None):
    # send_telegram_document_task: Envía  telegram document task. Args: datos del mensaje. Returns: resultado del envío.
    from apps.communications.services.telegram_unified import TelegramNotificationService

    try:
        agencia = None
        if agencia_id:
            from core.models.agencia import Agencia

            agencia = Agencia.objects.get(pk=agencia_id)
        result = TelegramNotificationService.send_document(
            file_path=file_path, caption=caption, chat_id=chat_id, agencia=agencia
        )
        if result:
            logger.info(f"Telegram document sent (file={file_path})")
        else:
            logger.warning(f"Telegram document send returned failure (file={file_path})")
        return result
    except Exception as exc:
        logger.error(f"Telegram document task error: {exc}")
        self.retry(exc=exc)


@shared_task(
    bind=True,
    queue="default",
    max_retries=3,
    default_retry_delay=60,
    time_limit=120,
    soft_time_limit=100,
)
def send_telegram_photo_task(self, agencia_id, filename="logo.png"):
    # send_telegram_photo_task: Envía  telegram photo task. Args: datos del mensaje. Returns: resultado del envío.
    from apps.communications.services.telegram_unified import upload_logo_to_telegram
    from core.models.agencia import Agencia

    try:
        agencia = Agencia.objects.get(pk=agencia_id)
        branding = agencia.branding
        if not branding or not branding.logo:
            logger.warning(f"Agencia {agencia_id} sin branding o logo")
            return False
        file_id = upload_logo_to_telegram(branding.logo.file, branding.logo.name)
        if file_id:
            branding.logo_telegram_id = file_id
            branding.logo_base64 = None
            branding.save(update_fields=["logo_telegram_id", "logo_base64"])
            logger.info(f"Logo subido a Telegram para agencia {agencia_id}: {file_id}")
        return bool(file_id)
    except Exception as exc:
        logger.error(f"Telegram photo task error for agencia {agencia_id}: {exc}")
        self.retry(exc=exc)


@shared_task(
    bind=True,
    queue="default",
    max_retries=3,
    default_retry_delay=30,
    time_limit=120,
    soft_time_limit=100,
)
def send_factura_to_telegram_task(self, factura_id):
    # send_factura_to_telegram_task: Envía  factura to telegram task. Args: datos del mensaje. Returns: resultado del envío.
    from apps.finance.models import Factura
    from apps.finance.services.factura_service import FacturaService

    try:
        factura = Factura.objects.get(pk=factura_id)
        result = FacturaService.send_to_telegram_if_needed(factura)
        if result:
            logger.info(f"Factura {factura_id} enviada a Telegram")
        return result
    except Exception as exc:
        logger.error(f"Error sending factura {factura_id} to Telegram: {exc}")
        self.retry(exc=exc)


@shared_task(
    bind=True,
    queue="notifications",
    max_retries=2,
    default_retry_delay=10,
    time_limit=30,
    soft_time_limit=20,
)
def answer_telegram_callback_task(self, bot_token, query_id, text):
    # answer_telegram_callback_task: Answer telegram callback task. Args: según implementación. Returns: según implementación.
    import requests

    url = f"https://api.telegram.org/bot{bot_token}/answerCallbackQuery"
    payload = {"callback_query_id": query_id, "text": text, "show_alert": False}
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code != 200:
            logger.error(f"Error en answerCallbackQuery: {response.text}")
        return response.status_code == 200
    except Exception as exc:
        logger.error(f"Error en answerCallbackQuery: {exc}")
        self.retry(exc=exc)


@shared_task(
    bind=True,
    queue="notifications",
    max_retries=2,
    default_retry_delay=10,
    time_limit=30,
    soft_time_limit=20,
)
def edit_telegram_message_task(self, bot_token, chat_id, message_id, text):
    # edit_telegram_message_task: Edit telegram message task. Args: según implementación. Returns: según implementación.
    import requests

    url = f"https://api.telegram.org/bot{bot_token}/editMessageText"
    payload = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text,
        "parse_mode": "HTML",
        "reply_markup": {"inline_keyboard": []},
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code != 200:
            logger.error(f"Error en editMessageText: {response.text}")
        return response.status_code == 200
    except Exception as exc:
        logger.error(f"Error en editMessageText: {exc}")
        self.retry(exc=exc)


@shared_task(
    bind=True,
    queue="notifications",
    max_retries=3,
    default_retry_delay=30,
    time_limit=60,
    soft_time_limit=50,
)
def get_telegram_file_url_task(self, file_id, agencia_id=None):
    # get_telegram_file_url_task: Obtiene/recupera telegram file url task. Args: según implementación. Returns: dato solicitado.
    from apps.communications.services.telegram_unified import TelegramNotificationService

    try:
        agencia = None
        if agencia_id:
            from core.models.agencia import Agencia

            agencia = Agencia.objects.get(pk=agencia_id)
        url = TelegramNotificationService.get_file_url(file_id, agencia=agencia)
        logger.info(f"Telegram file URL resolved for file_id={file_id}")
        return url
    except Exception as exc:
        logger.error(f"Telegram file URL task error: {exc}")
        self.retry(exc=exc)


@shared_task(queue="notifications", max_retries=3, default_retry_delay=30, time_limit=60)
def send_telegram_to_client_task(
    cliente_id, message, parse_mode="HTML", document_url=None, caption=None
):
    """Envía un mensaje de Telegram a un cliente."""
    from apps.communications.services.telegram_unified import send_telegram_to_client
    from apps.crm.models import Cliente

    try:
        cliente = Cliente.objects.get(pk=cliente_id)
        success = send_telegram_to_client(cliente, message, parse_mode, document_url, caption)
        logger.info(
            f"Telegram to client {cliente_id}: {'OK' if success else 'FAILED (no chat_id)'}"
        )
        return success
    except Cliente.DoesNotExist:
        logger.error(f"Cliente {cliente_id} no encontrado")
        return False


@shared_task(queue="notifications", max_retries=3, default_retry_delay=30, time_limit=60)
def notify_cliente_confirmacion_venta_task(venta_id):
    """Envía confirmación de venta al cliente por Telegram."""
    from apps.communications.services.telegram_unified import notify_cliente_confirmacion_venta
    from apps.sales.models import Venta

    try:
        venta = Venta.objects.select_related("cliente").get(pk=venta_id)
        return notify_cliente_confirmacion_venta(venta.cliente, venta)
    except Exception as e:
        logger.error(f"Error notificando venta {venta_id} por Telegram: {e}")
        return False


@shared_task(queue="notifications", max_retries=3, default_retry_delay=30, time_limit=60)
def notify_cliente_recordatorio_pago_task(venta_id):
    """Envía recordatorio de pago al cliente por Telegram."""
    from apps.communications.services.telegram_unified import notify_cliente_recordatorio_pago
    from apps.sales.models import Venta

    try:
        venta = Venta.objects.select_related("cliente").get(pk=venta_id)
        return notify_cliente_recordatorio_pago(venta.cliente, venta)
    except Exception as e:
        logger.error(f"Error notificando recordatorio {venta_id} por Telegram: {e}")
        return False


@shared_task(queue="notifications", max_retries=3, default_retry_delay=30, time_limit=60)
def notify_cliente_alerta_migratoria_task(cliente_id, destino, requisitos):
    """Envía alerta migratoria al cliente por Telegram."""
    from apps.communications.services.telegram_unified import notify_cliente_alerta_migratoria
    from apps.crm.models import Cliente

    try:
        cliente = Cliente.objects.get(pk=cliente_id)
        return notify_cliente_alerta_migratoria(cliente, destino, requisitos)
    except Exception as e:
        logger.error(f"Error notificando alerta migratoria a cliente {cliente_id}: {e}")
        return False

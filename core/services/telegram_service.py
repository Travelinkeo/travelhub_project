
import logging
from .telegram_notification_service import TelegramNotificationService

logger = logging.getLogger(__name__)

def enviar_alerta_telegram(mensaje: str):
    """
    Shim para soportar la función 'enviar_alerta_telegram' 
    utilizando el servicio unificado TelegramNotificationService.
    """
    success = TelegramNotificationService.send_message(mensaje)
    if success:
        logger.info("Telegram alert sent successfully.")
    else:
        logger.error("Failed to send Telegram alert.")
    return success

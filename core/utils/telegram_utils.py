# core/utils/telegram_utils.py

import os
import logging
import asyncio
from telegram import Bot
from django.conf import settings

logger = logging.getLogger(__name__)

async def send_telegram_alert(message, token=None, target_chat_id=None):
    """
    Envía una alerta al Grupo Configurado (o al Admin si no hay grupo).
    Ideal para notificaciones de sistema, pagos, errores, etc.
    """
    token = token or os.getenv('TELEGRAM_BOT_TOKEN')
    if not target_chat_id:
        admin_id = os.getenv('TELEGRAM_ADMIN_ID')
        group_id = os.getenv('TELEGRAM_GROUP_ID')
        # Prioridad: Grupo (para que lo vea el equipo), sino Admin
        target_chat_id = group_id if group_id else admin_id

    if not token or not target_chat_id:
        logger.warning("Telegram Config incompleto (Falta Token o Target ID).")
        return False

    try:
        bot = Bot(token=token)
        await bot.send_message(chat_id=target_chat_id, text=message, parse_mode='HTML')
        return True
    except Exception as e:
        logger.error(f"Error enviando alerta Telegram: {e}")
        return False

def send_telegram_alert_sync(message, token=None, target_chat_id=None):
    """
    Wrapper síncrono para usar en contextos donde no se puede usar async/await
    """
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(send_telegram_alert(message, token, target_chat_id))
        loop.close()
    except Exception as e:
        logger.error(f"Error en wrapper síncrono de Telegram: {e}")

async def send_telegram_file(file_path, caption=None, token=None, target_chat_id=None):
    """
    Envía un archivo (PDF, imagen, etc.) al Grupo o Admin.
    """
    token = token or os.getenv('TELEGRAM_BOT_TOKEN')
    if not target_chat_id:
        admin_id = os.getenv('TELEGRAM_ADMIN_ID')
        group_id = os.getenv('TELEGRAM_GROUP_ID')
        target_chat_id = group_id if group_id else admin_id

    if not token or not target_chat_id:
        return False

    try:
        if not os.path.exists(file_path):
            logger.error(f"Archivo no encontrado para enviar a Telegram: {file_path}")
            return False

        bot = Bot(token=token)
        with open(file_path, 'rb') as f:
            await bot.send_document(
                chat_id=target_chat_id, 
                document=f, 
                caption=caption,
                parse_mode='HTML',
                read_timeout=30,
                write_timeout=30,
                connect_timeout=30
            )
        return True
    except Exception as e:
        logger.error(f"Error enviando archivo Telegram: {e}")
        return False

def send_telegram_file_sync(file_path, caption=None, token=None, target_chat_id=None):
    """Wrapper síncrono para enviar archivos."""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(send_telegram_file(file_path, caption, token, target_chat_id))
        loop.close()
    except Exception as e:
        logger.error(f"Error en wrapper síncrono de Telegram (File): {e}")


import logging
import os
import requests
from django.conf import settings
from telegram import Bot
from telegram.error import TelegramError

logger = logging.getLogger(__name__)

class TelegramStorageService:
    """
    Servicio para usar un Canal de Telegram como almacenamiento ilimitado.
    Sube archivos recuperando su file_id y permite generar links temporales.
    """
    
    def __init__(self):
        self.bot_token = getattr(settings, 'TELEGRAM_BOT_TOKEN', None)
        # ID del canal donde se guardarán los archivos "DB"
        # Debería estar en settings, por ahora usamos una variable de entorno o hardcoded temporal
        self.storage_channel_id = os.environ.get('TELEGRAM_STORAGE_CHANNEL_ID', None) 
        
        if not self.bot_token:
            logger.warning("TELEGRAM_BOT_TOKEN no configurado. TelegramStorageService deshabilitado.")

    async def upload_file(self, file_path_or_buffer, filename="documento.pdf", caption=None):
        """
        Sube un archivo a Telegram y retorna su file_id.
        """
        if not self.bot_token or not self.storage_channel_id:
            logger.error("Falta configuración de Telegram (Token o Channel ID)")
            return None
            
        try:
            bot = Bot(token=self.bot_token)
            
            logger.info(f"Subiendo {filename} a Telegram Storage ({self.storage_channel_id})...")
            
            # Si es un path string, abrirlo
            if isinstance(file_path_or_buffer, str):
                with open(file_path_or_buffer, 'rb') as f:
                    message = await bot.send_document(
                        chat_id=self.storage_channel_id,
                        document=f,
                        filename=filename,
                        caption=caption
                    )
            else:
                # Asumimos que es un buffer (BytesIO)
                message = await bot.send_document(
                    chat_id=self.storage_channel_id,
                    document=file_path_or_buffer,
                    filename=filename,
                    caption=caption
                )
                
            file_id = message.document.file_id
            logger.info(f"✅ Archivo subido exitosamente. File ID: {file_id}")
            return file_id
            
        except Exception as e:
            logger.error(f"Error subiendo archivo a Telegram: {e}")
            return None

    async def get_file_url(self, file_id):
        """
        Obtiene una URL temporal de descarga para un file_id.
        Nota: Esta URL expira en 1 hora.
        """
        if not self.bot_token:
            return None
            
        try:
            bot = Bot(token=self.bot_token)
            file_obj = await bot.get_file(file_id)
            return file_obj.file_path
        except Exception as e:
            logger.error(f"Error recuperando URL de archivo Telegram {file_id}: {e}")
            return None

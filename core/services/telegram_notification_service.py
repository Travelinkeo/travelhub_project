import logging
import os
import requests
from django.conf import settings

# 🔒 PADLOCK: CRITICAL INFRASTRUCTURE
# This service handles Telegram API communications.
# LOGIC IS LOCKED. DO NOT MODIFY WITHOUT EXPLICIT AUTHORIZATION.
# Maintained by: Antigravity/Gemini
# -----------------------------------------------------

logger = logging.getLogger(__name__)

class TelegramNotificationService:
    """
    Servicio unificado para enviar notificaciones y archivos a Telegram.
    Centraliza la lógica de envío para Boletos, Facturas y otros documentos.
    """

    @staticmethod
    def send_message(message: str, chat_id: str = None, parse_mode: str = 'HTML', agencia=None):
        """Envía un mensaje de texto simple."""
        try:
            # SaaS Logic: Prioritize Agency Config
            token = settings.TELEGRAM_BOT_TOKEN
            if agencia and agencia.configuracion_api.get('TELEGRAM_BOT_TOKEN'):
                token = agencia.configuracion_api.get('TELEGRAM_BOT_TOKEN')
            
            # Chat ID Logic
            chat = chat_id
            if not chat:
                 if agencia:
                     chat = agencia.configuracion_api.get('TELEGRAM_CHANNEL_ID') or agencia.configuracion_api.get('TELEGRAM_GROUP_ID')
                 
                 # Fallback global settings
                 if not chat:
                     chat = getattr(settings, 'TELEGRAM_GROUP_ID', None) or getattr(settings, 'TELEGRAM_CHANNEL_ID', None)
            
            if not token or not chat:
                logger.warning(f"Telegram Config Missing: Token={bool(token)}, Chat={chat} (Agencia: {agencia})")
                return False

            url = f"https://api.telegram.org/bot{token}/sendMessage"
            payload = {
                'chat_id': chat,
                'text': message,
                'parse_mode': parse_mode
            }
            response = requests.post(url, data=payload, timeout=30)
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Error sending Telegram message: {e}")
            return False

    @staticmethod
    def send_document(file_path: str, caption: str = None, chat_id: str = None, agencia=None):
        """Envía un documento (PDF, etc.) a Telegram via Path Local o URL."""
        try:
            # SaaS Logic: Prioritize Agency Config
            token = settings.TELEGRAM_BOT_TOKEN
            if agencia and agencia.configuracion_api.get('TELEGRAM_BOT_TOKEN'):
                token = agencia.configuracion_api.get('TELEGRAM_BOT_TOKEN')

            # Chat ID Logic
            chat = chat_id
            if not chat:
                if agencia:
                    chat = agencia.configuracion_api.get('TELEGRAM_STORAGE_CHANNEL_ID') or agencia.configuracion_api.get('TELEGRAM_CHANNEL_ID') or agencia.configuracion_api.get('TELEGRAM_GROUP_ID')
                
                # Fallback Global
                if not chat:
                    chat = getattr(settings, 'TELEGRAM_STORAGE_CHANNEL_ID', None) or getattr(settings, 'TELEGRAM_GROUP_ID', None)

            if not token or not chat:
                logger.warning(f"Telegram Config Missing: Token={bool(token)}, Chat={chat}")
                return False

            url_api = f"https://api.telegram.org/bot{token}/sendDocument"
            
            # Caso 1: Es una URL (Cloudinary / S3)
            if file_path.startswith('http'):
                logger.info(f"Enviando documento vía URL: {file_path}")
                data = {
                    'chat_id': chat,
                    'document': file_path, # Telegram descarga desde la URL
                    'caption': caption,
                    'parse_mode': 'HTML'
                }
                response = requests.post(url_api, data=data, timeout=60)

            # Caso 2: Es un archivo local REVISADO
            elif os.path.exists(file_path):
                with open(file_path, 'rb') as f:
                    files = {'document': f}
                    data = {'chat_id': chat}
                    if caption:
                        data['caption'] = caption
                        data['parse_mode'] = 'HTML'
                    
                    response = requests.post(url_api, data=data, files=files, timeout=60)
            
            # Caso 3: Es un FILE ID (Reenvío desde Telegram Cloud)
            else:
                # Asumimos que es un file_id si no es path ni url
                logger.info(f"Enviando documento vía File ID: {file_path}")
                data = {
                    'chat_id': chat,
                    'document': file_path, # File ID
                    'caption': caption,
                    'parse_mode': 'HTML'
                }
                response = requests.post(url_api, data=data, timeout=60)
            
            # Verificar respuesta
            if response.status_code != 200:
                logger.error(f"Telegram API Error: {response.text}")
                response.raise_for_status()
            
            # Extraer file_id para almacenamiento "Nube Telegram"
            try:
                resp_json = response.json()
                if resp_json.get('ok'):
                    document = resp_json['result'].get('document')
                    file_id = document.get('file_id') if document else None
                    if file_id:
                        logger.info(f"✅ Documento enviado. File ID: {file_id}")
                        return file_id # Retornar ID para guardar en DB
            except Exception as e_json:
                 logger.warning(f"No se pudo extraer file_id de Telegram: {e_json}")

            return True # Retorna True si se envió pero no se sacó ID (compatibilidad)
                
        except Exception as e:
            logger.error(f"Error sending Telegram document: {e}")
            return False

    @staticmethod
    def get_file_url(file_id: str, agencia=None):
        """
        Obtiene la URL temporal de descarga de un archivo de Telegram.
        NOTA: La URL contiene el Token del Bot. Idealmente usar un Proxy View.
        """
        try:
            token = settings.TELEGRAM_BOT_TOKEN
            if agencia and agencia.configuracion_api.get('TELEGRAM_BOT_TOKEN'):
                token = agencia.configuracion_api.get('TELEGRAM_BOT_TOKEN')
                
            if not token:
                return None
            
            # 1. Obtener path del archivo
            url_api = f"https://api.telegram.org/bot{token}/getFile"
            response = requests.post(url_api, data={'file_id': file_id}, timeout=30)
            
            if response.status_code == 200:
                result = response.json().get('result', {})
                file_path = result.get('file_path')
                
                if file_path:
                    # 2. Construir URL completa
                    # https://api.telegram.org/file/bot<token>/<file_path>
                    return f"https://api.telegram.org/file/bot{token}/{file_path}"
            
            logger.error(f"Error getting file info from Telegram: {response.text}")
            return None

        except Exception as e:
            logger.error(f"Error resolving Telegram file URL: {e}")
            return None

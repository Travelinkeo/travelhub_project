import requests
import logging
import os
from django.conf import settings

logger = logging.getLogger(__name__)

class WhatsAppService:
    """
    Servicio para interactuar con el microservicio WAHA (WhatsApp HTTP API).
    Proporciona métodos para gestionar la sesión, obtener el QR y enviar mensajes.
    """
    
    @classmethod
    def _get_base_url(cls):
        # Internamente en Docker usamos el puerto 3000 para WAHA
        return os.getenv('WHATSAPP_MICROSERVICE_URL', 'http://wppconnect:3000')

    @classmethod
    def _get_headers(cls):
        token = os.getenv('WHATSAPP_MICROSERVICE_TOKEN', 'THISISMYSECURETOKEN')
        return {
            "X-Api-Key": token,
            "Content-Type": "application/json"
        }

    @classmethod
    def get_status(cls, session_name: str):
        """Obtiene el estado de la sesión. WAHA Core solo usa 'default'."""
        session_name = "default"
        url = f"{cls._get_base_url()}/api/sessions/"
        try:
            response = requests.get(url, headers=cls._get_headers(), timeout=10)
            if response.status_code == 200:
                sessions = response.json()
                for session in sessions:
                    if session.get('name') == session_name:
                        # WAHA status: STOPPED, STARTING, SCAN_QR_CODE, WORKING, FAILED
                        return session.get('status', 'STOPPED').upper()
                return "DISCONNECTED"
            return "DISCONNECTED"
        except Exception as e:
            logger.error(f"❌ [WPP] Error obteniendo estado: {e}")
            return "DISCONNECTED"

    @classmethod
    def start_session(cls, session_name: str):
        """Inicia una nueva sesión si no existe."""
        session_name = "default"
        url = f"{cls._get_base_url()}/api/sessions/start"
        payload = {
            "name": session_name,
            "config": {
                "engine": "WEBJS",
                "browser": {
                    "executablePath": "/usr/bin/chromium",
                    "args": ["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
                }
            }
        }
        try:
            response = requests.post(url, json=payload, headers=cls._get_headers(), timeout=30)
            return response.json()
        except Exception as e:
            logger.error(f"❌ [WPP] Error al iniciar sesión: {e}")
            return None

    @classmethod
    def get_qr_code(cls, session_name: str):
        """Obtiene el código QR actual de la sesión en base64."""
        session_name = "default"
        url = f"{cls._get_base_url()}/api/{session_name}/auth/qr"
        try:
            response = requests.get(url, headers=cls._get_headers(), timeout=10)
            if response.status_code == 200:
                import base64
                encoded_string = base64.b64encode(response.content).decode('utf-8')
                return f"data:image/png;base64,{encoded_string}"
            return None
        except Exception as e:
            return None

    @classmethod
    def send_message(cls, chat_id: str, text: str, session_name: str = "default"):
        """
        Envía un mensaje de texto.
        """
        session_name = "default"
        url = f"{cls._get_base_url()}/api/sendText"
        
        if not chat_id.endswith('@c.us') and not chat_id.endswith('@g.us'):
            clean_id = ''.join(filter(str.isdigit, chat_id))
            chat_id = f"{clean_id}@c.us"

        payload = {
            "session": session_name,
            "chatId": chat_id,
            "text": text
        }
        
        try:
            response = requests.post(url, json=payload, headers=cls._get_headers(), timeout=20)
            return response.status_code in [200, 201]
        except Exception as e:
            logger.error(f"❌ Excepción enviando mensaje: {e}")
            return False

    @classmethod
    def logout(cls, session_name: str):
        """Cierra la sesión."""
        session_name = "default"
        url = f"{cls._get_base_url()}/api/sessions/stop"
        payload = {"name": session_name}
        try:
            response = requests.post(url, json=payload, headers=cls._get_headers(), timeout=10)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"❌ [WPP] Error al cerrar sesión: {e}")
            return False

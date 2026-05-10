import os
import logging
import requests
import json
from django.conf import settings

logger = logging.getLogger(__name__)

class EvolutionService:
    """
    Servicio avanzado para interactuar con Evolution API v2.
    Permite el manejo de múltiples instancias (una por agencia) y el envío de media.
    """

    @classmethod
    def _get_base_url(cls):
        return os.getenv('WHATSAPP_MICROSERVICE_URL', 'http://evolution:8080')

    @classmethod
    def _get_headers(cls):
        return {
            "apikey": os.getenv('WHATSAPP_MICROSERVICE_TOKEN', 'THISISMYSECURETOKEN'),
            "Content-Type": "application/json"
        }

    @classmethod
    def create_instance(cls, instance_name: str):
        """Crea una nueva instancia en Evolution API (Soporta v1 y v2)."""
        url = f"{cls._get_base_url()}/instance/create"
        payload = {
            "instanceName": instance_name,
            "token": settings.SECRET_KEY[:16], 
            "qrcode": True
        }
        # Nota: En v2 se requiere 'integration', pero en v1 no. 
        # Intentamos v1 por defecto si v2 falla o viceversa.
        try:
            response = requests.post(url, json=payload, headers=cls._get_headers(), timeout=30)
            if response.status_code == 400 and "integration" in response.text:
                # Reintento con v2 payload
                payload["integration"] = "WHATSAPP-BAILEYS"
                response = requests.post(url, json=payload, headers=cls._get_headers(), timeout=30)
            
            if response.status_code in [200, 201]:
                logger.info(f"✅ Instancia Evolution '{instance_name}' manejada.")
                return response.json()
            else:
                logger.error(f"❌ Error creando instancia: {response.text}")
                return None
        except Exception as e:
            logger.error(f"❌ Excepción en create_instance: {e}")
            return None

    @classmethod
    def get_instance_state(cls, instance_name: str):
        """Retorna el estado crudo de la instancia (open, connecting, close)."""
        url = f"{cls._get_base_url()}/instance/connectionState/{instance_name}"
        try:
            response = requests.get(url, headers=cls._get_headers(), timeout=5)
            if response.status_code == 200:
                data = response.json()
                # Evolution v1.8.2 retorna el estado en data['instance']['state']
                state = data.get('instance', {}).get('state')
                logger.info(f"🔍 Evolution API: Instance '{instance_name}' state is '{state}'")
                return state
            else:
                logger.warning(f"⚠️ Evolution API get_instance_state returned {response.status_code}: {response.text}")
        except Exception as e:
            logger.error(f"❌ Evolution API get_instance_state error: {e}")
            pass
        return "disconnected"

    @classmethod
    def get_connection_status(cls, instance_name: str):
        """Mantiene compatibilidad devolviendo True solo si está 'open'."""
        return cls.get_instance_state(instance_name) == 'open'

    @classmethod
    def get_qr_code(cls, instance_name: str):
        """Obtiene el QR para conectar la instancia."""
        url = f"{cls._get_base_url()}/instance/connect/{instance_name}"
        try:
            response = requests.get(url, headers=cls._get_headers(), timeout=20)
            if response.status_code == 200:
                data = response.json()
                # v1 retorna directamente el link o base64 en algunos casos, v2 en 'base64'
                if isinstance(data, dict):
                    return data.get('base64') or data.get('code') or data
                return data
            return None
        except Exception as e:
            logger.error(f"❌ Error obteniendo QR: {e}")
            return None

    @classmethod
    def send_text(cls, instance_name: str, number: str, text: str):
        """Envía un mensaje de texto simple con auto-provisioning."""
        # --- AUTO-PROVISIONING ---
        if not cls.get_connection_status(instance_name):
            logger.info(f"Instancia '{instance_name}' no encontrada o cerrada. Intentando crear/reiniciar...")
            cls.create_instance(instance_name)
            # Damos un pequeño margen para que la instancia suba (aunque el mensaje podría fallar la primera vez)
        # -------------------------

        url = f"{cls._get_base_url()}/message/sendText/{instance_name}"
        
        # Limpiar número
        clean_number = "".join(filter(str.isdigit, str(number)))
        
        payload = {
            "number": clean_number,
            "options": {
                "delay": 1200,
                "presence": "composing",
                "linkPreview": True
            },
            "textMessage": {
                "text": text
            }
        }
        
        try:
            response = requests.post(url, json=payload, headers=cls._get_headers(), timeout=20)
            if response.status_code in [200, 201]:
                logger.info(f"✅ WhatsApp (Evolution) enviado a {clean_number}")
                return True
            logger.error(f"❌ Error Evolution sendText: {response.text}")
            return False
        except Exception as e:
            logger.error(f"❌ Excepción Evolution sendText: {e}")
            return False

    @classmethod
    def send_media(cls, instance_name: str, number: str, media_url: str, caption: str = "", file_name: str = "documento.pdf"):
        """
        Envía un archivo (PDF, Imagen) vía Evolution API con auto-provisioning.
        """
        # --- AUTO-PROVISIONING ---
        if not cls.get_connection_status(instance_name):
            cls.create_instance(instance_name)
        # -------------------------

        url = f"{cls._get_base_url()}/message/sendMedia/{instance_name}"
        
        clean_number = "".join(filter(str.isdigit, str(number)))
        
        # Detectar mimetypes básicos por extensión
        mimetype = "application/pdf"
        if media_url.lower().endswith(('.png', '.jpg', '.jpeg')):
            mimetype = "image/jpeg"

        payload = {
            "number": clean_number,
            "mediaMessage": {
                "mediatype": "document" if "pdf" in mimetype else "image",
                "media": media_url,
                "fileName": file_name,
                "caption": caption
            }
        }
        
        try:
            response = requests.post(url, json=payload, headers=cls._get_headers(), timeout=30)
            if response.status_code in [200, 201]:
                logger.info(f"✅ Media Evolution enviado a {clean_number}")
                return True
            logger.error(f"❌ Error Evolution sendMedia: {response.text}")
            return False
        except Exception as e:
            logger.error(f"❌ Excepción Evolution sendMedia: {e}")
            return False
    @classmethod
    def delete_instance(cls, instance_name: str):
        """Elimina/Desconecta una instancia de Evolution API."""
        url = f"{cls._get_base_url()}/instance/delete/{instance_name}"
        try:
            response = requests.delete(url, headers=cls._get_headers(), timeout=20)
            return response.status_code in [200, 201, 204]
        except Exception as e:
            logger.error(f"❌ Error eliminando instancia: {e}")
            return False

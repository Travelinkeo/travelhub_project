import logging
import os

import requests
from django.conf import settings

from apps.common.services.circuit_breaker import whatsapp_circuit_breaker

logger = logging.getLogger(__name__)

class EvolutionService:
    """
    Servicio avanzado para interactuar con Evolution API v2.
    Permite el manejo de múltiples instancias (una por agencia) y el envío de media.
    """

    @classmethod
    def _get_base_url(cls):
        return getattr(settings, 'WHATSAPP_MICROSERVICE_URL', None) or os.getenv('WHATSAPP_MICROSERVICE_URL', 'http://evolution:8080')

    @classmethod
    def _get_headers(cls):
        token = getattr(settings, 'WHATSAPP_MICROSERVICE_TOKEN', None) or os.getenv('WHATSAPP_MICROSERVICE_TOKEN')
        if not token:
            raise ValueError("WHATSAPP_MICROSERVICE_TOKEN no configurado")
        return {
            "apikey": token,
            "Content-Type": "application/json",
        }

    @classmethod
    def create_instance(cls, instance_name: str):
        """Crea una nueva instancia en Evolution API v2."""
        url = f"{cls._get_base_url()}/instance/create"
        payload = {
            "instanceName": instance_name,
            "token": settings.SECRET_KEY[:16],
            "qrcode": True,
            "integration": "WHATSAPP-BAILEYS",
        }
        try:
            response = requests.post(url, json=payload, headers=cls._get_headers(), timeout=30)
            if response.status_code in [200, 201]:
                logger.info(f"Instancia Evolution '{instance_name}' creada.")
                return response.json()
            logger.error(f"Error creando instancia: {response.status_code} {response.text[:300]}")
            return None
        except Exception as e:
            logger.error(f"Excepcion en create_instance: {e}")
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
        """
        Obtiene el QR para conectar la instancia.

        Evolution API v2.2.x no expone QR code via REST directamente.
        El QR se genera en la respuesta de POST /instance/create (campo 'qrcode')
        y se visualiza en el Manager UI: /manager/qr/{instance_name}
        """
        url = f"{cls._get_base_url()}/instance/connect/{instance_name}"
        try:
            response = requests.get(url, headers=cls._get_headers(), timeout=20)
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, dict):
                    base64 = data.get("base64") or data.get("code")
                    if base64:
                        return base64
            logger.info(f"QR no disponible via REST para '{instance_name}'. Usa Manager UI.")
            return None
        except Exception as e:
            logger.error(f"Error obteniendo QR: {e}")
            return None

    @classmethod
    def get_manager_qr_url(cls, instance_name: str):
        """Retorna la URL de la imagen QR (endpoint propio que captura el QR via WebSocket)."""
        return f"/whatsapp/qr-img/{instance_name}/"

    @classmethod
    def get_pairing_code(cls, instance_name: str, phone_number: str):
        """Obtiene un codigo de emparejamiento (pairing code) para vincular sin QR."""
        url = f"{cls._get_base_url()}/instance/connect/{instance_name}"
        clean_number = "".join(filter(str.isdigit, str(phone_number)))
        try:
            payload = {"phone": clean_number}
            response = requests.post(url, json=payload, headers=cls._get_headers(), timeout=20)
            if response.status_code in [200, 201]:
                data = response.json()
                code = data.get("code") if isinstance(data, dict) else data
                return {"success": True, "code": code, "numero": clean_number}
            return {"success": False, "error": f"Error {response.status_code}: {response.text[:200]}"}
        except Exception as e:
            logger.error(f"Error obteniendo pairing code: {e}")
            return {"success": False, "error": str(e)}

    @classmethod
    def send_text(cls, instance_name: str, number: str, text: str):
        """Envía un mensaje de texto simple con auto-provisioning y circuit breaker."""
        return whatsapp_circuit_breaker.call(cls._send_text_internal, instance_name, number, text)

    @classmethod
    def _send_text_internal(cls, instance_name: str, number: str, text: str):
        """Internal send implementation protected by circuit breaker."""
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
        """Envía un archivo (PDF, Imagen) vía Evolution API con circuit breaker."""
        return whatsapp_circuit_breaker.call(cls._send_media_internal, instance_name, number, media_url, caption, file_name)

    @classmethod
    def _send_media_internal(cls, instance_name: str, number: str, media_url: str, caption: str = "", file_name: str = "documento.pdf"):
        """Internal media send implementation protected by circuit breaker."""
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

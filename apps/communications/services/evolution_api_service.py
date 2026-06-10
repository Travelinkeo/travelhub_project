import logging
import os

import requests
from django.conf import settings
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

from apps.common.services.circuit_breaker import whatsapp_circuit_breaker

logger = logging.getLogger(__name__)


class EvolutionService:
    """
    Servicio avanzado para interactuar con Evolution API v2.
    Permite el manejo de múltiples instancias (una por agencia) y el envío de media.
    """

    @classmethod
    def _get_base_url(cls):
        return getattr(settings, "WHATSAPP_MICROSERVICE_URL", None) or os.getenv(
            "WHATSAPP_MICROSERVICE_URL", "http://evolution:8080"
        )

    @classmethod
    def _get_headers(cls):
        token = getattr(settings, "WHATSAPP_MICROSERVICE_TOKEN", None) or os.getenv(
            "WHATSAPP_MICROSERVICE_TOKEN"
        )
        if not token:
            raise ValueError("WHATSAPP_MICROSERVICE_TOKEN no configurado")
        return {
            "apikey": token,
            "Content-Type": "application/json",
        }

    @classmethod
    def _get_session(cls) -> requests.Session:
        session = requests.Session()
        retries = Retry(
            total=3,
            backoff_factor=0.3,
            status_forcelist=[500, 502, 503, 504],
            raise_on_status=False,
        )
        session.mount("http://", HTTPAdapter(max_retries=retries))
        session.mount("https://", HTTPAdapter(max_retries=retries))
        return session

    @classmethod
    def create_instance(cls, instance_name: str):
        """Crea una nueva instancia en Evolution API v2."""
        url = f"{cls._get_base_url()}/instance/create"
        payload = {
            "instanceName": instance_name,
            "token": settings.EVOLUTION_INSTANCE_TOKEN,
            "qrcode": True,
            "integration": "WHATSAPP-BAILEYS",
        }
        try:
            session = cls._get_session()
            response = session.post(
                url,
                json=payload,
                headers=cls._get_headers(),
                timeout=(3.05, 10),  # connect, read
            )
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
            session = cls._get_session()
            response = session.get(
                url,
                headers=cls._get_headers(),
                timeout=(3.05, 5),  # connect, read
            )
            if response.status_code == 200:
                data = response.json()
                state = data.get("instance", {}).get("state")
                logger.info(f"🔍 Evolution API: Instance '{instance_name}' state is '{state}'")
                return state
            else:
                logger.warning(
                    f"⚠️ Evolution API get_instance_state returned {response.status_code}: {response.text}"
                )
        except Exception as e:
            logger.error(f"❌ Evolution API get_instance_state error: {e}")
            pass
        return "disconnected"

    @classmethod
    def get_connection_status(cls, instance_name: str):
        """Mantiene compatibilidad devolviendo True solo si está 'open'."""
        return cls.get_instance_state(instance_name) == "open"

    @classmethod
    def get_qr_code(cls, instance_name: str):
        """Obtiene el QR para conectar la instancia."""
        url = f"{cls._get_base_url()}/instance/connect/{instance_name}"
        try:
            session = cls._get_session()
            response = session.get(
                url,
                headers=cls._get_headers(),
                timeout=(3.05, 10),  # connect, read
            )
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
        """Retorna la URL de la imagen QR."""
        try:
            from django.urls import reverse

            return reverse("core:evolution_qr_image", kwargs={"instance_name": instance_name})
        except Exception:
            return f"/system/whatsapp/qr-img/{instance_name}/"

    @classmethod
    def get_pairing_code(cls, instance_name: str, phone_number: str):
        """Obtiene un codigo de emparejamiento (pairing code) para vincular sin QR."""
        url = f"{cls._get_base_url()}/instance/connect/{instance_name}"
        clean_number = "".join(filter(str.isdigit, str(phone_number)))
        try:
            payload = {"phone": clean_number}
            session = cls._get_session()
            response = session.post(
                url,
                json=payload,
                headers=cls._get_headers(),
                timeout=(3.05, 10),  # connect, read
            )
            if response.status_code in [200, 201]:
                data = response.json()
                code = data.get("code") if isinstance(data, dict) else data
                return {"success": True, "code": code, "numero": clean_number}
            return {
                "success": False,
                "error": f"Error {response.status_code}: {response.text[:200]}",
            }
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
        if not cls.get_connection_status(instance_name):
            logger.info(
                f"Instancia '{instance_name}' no encontrada o cerrada. Intentando crear/reiniciar..."
            )
            cls.create_instance(instance_name)

        url = f"{cls._get_base_url()}/message/sendText/{instance_name}"
        clean_number = "".join(filter(str.isdigit, str(number)))

        payload = {
            "number": clean_number,
            "options": {"delay": 1200, "presence": "composing", "linkPreview": True},
            "textMessage": {"text": text},
        }

        try:
            session = cls._get_session()
            response = session.post(
                url,
                json=payload,
                headers=cls._get_headers(),
                timeout=(3.05, 10),  # connect, read
            )
            if response.status_code in [200, 201]:
                logger.info(f"✅ WhatsApp (Evolution) enviado a {clean_number}")
                return True
            logger.error(f"❌ Error Evolution sendText: {response.text}")
            return False
        except Exception as e:
            logger.error(f"❌ Excepción Evolution sendText: {e}")
            return False

    @classmethod
    def send_media(
        cls,
        instance_name: str,
        number: str,
        media_url: str,
        caption: str = "",
        file_name: str = "documento.pdf",
    ):
        """Envía un archivo (PDF, Imagen) vía Evolution API con circuit breaker."""
        return whatsapp_circuit_breaker.call(
            cls._send_media_internal, instance_name, number, media_url, caption, file_name
        )

    @classmethod
    def _send_media_internal(
        cls,
        instance_name: str,
        number: str,
        media_url: str,
        caption: str = "",
        file_name: str = "documento.pdf",
    ):
        """Internal media send implementation protected by circuit breaker."""
        if not cls.get_connection_status(instance_name):
            cls.create_instance(instance_name)

        url = f"{cls._get_base_url()}/message/sendMedia/{instance_name}"
        clean_number = "".join(filter(str.isdigit, str(number)))

        mimetype = "application/pdf"
        if media_url.lower().endswith((".png", ".jpg", ".jpeg")):
            mimetype = "image/jpeg"

        payload = {
            "number": clean_number,
            "mediaMessage": {
                "mediatype": "document" if "pdf" in mimetype else "image",
                "media": media_url,
                "fileName": file_name,
                "caption": caption,
            },
        }

        try:
            session = cls._get_session()
            response = session.post(
                url,
                json=payload,
                headers=cls._get_headers(),
                timeout=(3.05, 15),  # connect, read (media takes longer)
            )
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
            session = cls._get_session()
            response = session.delete(url, headers=cls._get_headers(), timeout=(3.05, 10))
            return response.status_code in [200, 201, 204]
        except Exception as e:
            logger.error(f"❌ Error eliminando instancia: {e}")
            return False

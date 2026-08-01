import logging

import requests
from django.conf import settings

from core.api import AgenciaConfiguracion

logger = logging.getLogger(__name__)


class WhatsAppEvolutionService:
    """
    Servicio para envío de notificaciones vía WhatsApp utilizando Evolution API.
    Implementado con arquitectura multi-tenant basada en AgenciaConfiguracion.
    """

    def __init__(self, agencia_id):
        """__init__."""
        self.agencia_id = agencia_id
        self.config = self._load_config()

    def _load_config(self):
        """Carga la configuración específica de la agencia."""
        try:
            return AgenciaConfiguracion.objects.get(agencia_id=self.agencia_id)
        except AgenciaConfiguracion.DoesNotExist:
            logger.error(f" Configuración no encontrada para la agencia {self.agencia_id}")
            return None

    def _get_headers(self):
        """_get_headers."""
        if not self.config or not self.config.evolution_api_key:
            # Fallback a settings globales si no hay específicos por agencia
            api_key = getattr(settings, "WHATSAPP_MICROSERVICE_TOKEN", None)
        else:
            api_key = self.config.evolution_api_key

        return {"apikey": api_key, "Content-Type": "application/json"}

    def _get_base_url(self):
        """_get_base_url."""
        if self.config and self.config.evolution_api_url:
            return self.config.evolution_api_url.rstrip("/")
        return getattr(settings, "WHATSAPP_MICROSERVICE_URL", "http://evolution:8080").rstrip("/")

    def _get_instance(self):
        """_get_instance."""
        if self.config and self.config.evolution_instance_name:
            return self.config.evolution_instance_name
        return f"agencia_{self.agencia_id}"

    def send_message(self, phone_number, text):
        """
        Envía un mensaje de texto simple.
        Endpoint: /message/sendText/{instance}
        """
        if not self.config:
            return False

        url = f"{self._get_base_url()}/message/sendText/{self._get_instance()}"

        # Limpiar número (solo dígitos)
        clean_number = "".join(filter(str.isdigit, str(phone_number)))

        payload = {
            "number": clean_number,
            "options": {"delay": 1200, "presence": "composing", "linkPreview": True},
            "textMessage": {"text": text},
        }

        try:
            response = requests.post(url, json=payload, headers=self._get_headers(), timeout=20)

            if response.status_code in [200, 201]:
                logger.info(f" WhatsApp enviado a {clean_number} (Agencia {self.agencia_id})")
                return True

            logger.error(f" Error Evolution API ({response.status_code}): {response.text}")
            return False

        except requests.exceptions.Timeout:
            logger.error(f" Timeout conectando con Evolution API para agencia {self.agencia_id}")
        except requests.exceptions.ConnectionError:
            logger.error(" Error de conexión con Evolution API")
        except Exception as e:
            logger.exception(f"❌ Excepción inesperada en send_message: {e}")

        return False

    def send_document(self, phone_number, document_url_or_base64, filename, caption=""):
        """
        Envía un documento (PDF) o imagen.
        Endpoint: /message/sendMedia/{instance}
        """
        if not self.config:
            return False

        url = f"{self._get_base_url()}/message/sendMedia/{self._get_instance()}"
        clean_number = "".join(filter(str.isdigit, str(phone_number)))

        # Detectar si es base64 o URL
        document_url_or_base64.startswith("data:") or len(document_url_or_base64) > 1000

        payload = {
            "number": clean_number,
            "mediaMessage": {
                "mediatype": "document",
                "media": document_url_or_base64,
                "fileName": filename,
                "caption": caption,
            },
        }

        try:
            response = requests.post(url, json=payload, headers=self._get_headers(), timeout=40)

            if response.status_code in [200, 201]:
                logger.info(f" Documento WhatsApp enviado a {clean_number}")
                return True

            logger.error(f" Error Evolution Media ({response.status_code}): {response.text}")
            return False

        except Exception as e:
            logger.error(f" Excepción en send_document: {e}")
            return False

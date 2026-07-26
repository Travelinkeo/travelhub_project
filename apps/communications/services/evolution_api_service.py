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
    def get_connection_qr_base64(cls, instance_name: str, timeout: int = 12):
        """Llama a Evolution /instance/connect y devuelve el QR en base64.

        Devuelve None si no hay QR disponible (versión exhaustiva de la API).

        Útil como fallback para garantizar que el frontend tenga SIEMPRE un data:image
        en cache, evitando el iframe roto (404) del Evolution Manager UI proxy.
        """
        from django.core.cache import cache

        url = f"{cls._get_base_url()}/instance/connect/{instance_name}"
        cache_key = f"evo_qr:{instance_name}"

        # Si ya está conectado a WhatsApp, no hay QR que mostrar.
        if cls.get_instance_state(instance_name) == "open":
            cache.delete(cache_key)
            return None

        try:
            session = cls._get_session()
            headers = cls._get_headers()
            headers.pop("Content-Type", None)
            response = session.get(url, headers=headers, timeout=(3.05, timeout))

            if response.status_code == 404:
                # La instancia no existe — intentar crearla y re-intentar
                cls.create_instance(instance_name)
                response = session.get(url, headers=headers, timeout=(3.05, timeout))

            if response.status_code == 200:
                data = response.json()
                qr_b64 = data.get("base64")
                if not qr_b64 and isinstance(data.get("qrcode"), dict):
                    qr_b64 = data["qrcode"].get("base64")
                if qr_b64:
                    if qr_b64.startswith("data:image"):
                        raw = qr_b64.split(",", 1)[1]
                    else:
                        raw = qr_b64
                    cache.set(cache_key, raw, 120)
                    return raw
        except Exception as e:
            logger.error(f"get_connection_qr_base64 error: {e}")
        return None

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

    # ==========================================================================
    # RICH MESSAGE TYPES (Buttons, Lists, Reactions, Location, Contact, Sticker)
    # ==========================================================================

    @classmethod
    def _ensure_instance(cls, instance_name: str):
        """Ensure instance exists and is connected, create if needed."""
        if not cls.get_connection_status(instance_name):
            logger.info(f"Instancia '{instance_name}' no conectada. Intentando crear...")
            cls.create_instance(instance_name)

    @classmethod
    def _clean_number(cls, number: str) -> str:
        return "".join(filter(str.isdigit, str(number)))

    @classmethod
    def send_buttons(cls, instance_name: str, number: str, text: str, buttons: list[dict]):
        """Envía un mensaje con botones interactivos.

        Args:
            instance_name: Nombre de la instancia Evolution
            number: Número de teléfono del destinatario
            text: Texto del mensaje
            buttons: Lista de botones. Cada botón: {"text": "Etiqueta", "id": "valor"}
                Ejemplo: [{"text": "Sí, quiero", "id": "confirmar"}, {"text": "No, gracias", "id": "rechazar"}]
                Máximo 3 botones.
        """
        return whatsapp_circuit_breaker.call(
            cls._send_buttons_internal, instance_name, number, text, buttons
        )

    @classmethod
    def _send_buttons_internal(
        cls, instance_name: str, number: str, text: str, buttons: list[dict]
    ):
        cls._ensure_instance(instance_name)
        url = f"{cls._get_base_url()}/message/sendButtons/{instance_name}"
        clean_number = cls._clean_number(number)

        payload = {
            "number": clean_number,
            "options": {"delay": 1200, "presence": "composing"},
            "buttonsMessage": {
                "text": text,
                "buttons": [
                    {"text": b.get("text", "Opción"), "id": b.get("id", str(i))}
                    for i, b in enumerate(buttons[:3])
                ],
            },
        }

        try:
            session = cls._get_session()
            response = session.post(
                url, json=payload, headers=cls._get_headers(), timeout=(3.05, 15)
            )
            if response.status_code in [200, 201]:
                logger.info(f"✅ Botones Evolution enviados a {clean_number}")
                return True
            logger.error(f"❌ Error Evolution sendButtons: {response.text[:300]}")
            return False
        except Exception as e:
            logger.error(f"❌ Excepción Evolution sendButtons: {e}")
            return False

    @classmethod
    def send_list(
        cls,
        instance_name: str,
        number: str,
        text: str,
        title: str,
        button_text: str,
        sections: list[dict],
    ):
        """Envía un mensaje con lista de opciones seleccionables.

        Args:
            instance_name: Nombre de la instancia Evolution
            number: Número de teléfono del destinatario
            text: Texto del mensaje (footer opcional)
            title: Título de la lista
            button_text: Texto del botón que abre la lista
            sections: Lista de secciones. Cada sección:
                {"title": "Título sección", "rows": [{"title": "Opción", "description": "Descripción", "id": "valor"}]}
                Ejemplo: [{"title": "Vuelos", "rows": [{"title": "Caracas-Madrid", "description": "ID 12345", "id": "vuelo_123"}]}]
        """
        return whatsapp_circuit_breaker.call(
            cls._send_list_internal, instance_name, number, text, title, button_text, sections
        )

    @classmethod
    def _send_list_internal(
        cls,
        instance_name: str,
        number: str,
        text: str,
        title: str,
        button_text: str,
        sections: list[dict],
    ):
        cls._ensure_instance(instance_name)
        url = f"{cls._get_base_url()}/message/sendList/{instance_name}"
        clean_number = cls._clean_number(number)

        payload = {
            "number": clean_number,
            "options": {"delay": 1200, "presence": "composing"},
            "listMessage": {
                "title": title,
                "text": text,
                "buttonText": button_text,
                "sections": sections,
            },
        }

        try:
            session = cls._get_session()
            response = session.post(
                url, json=payload, headers=cls._get_headers(), timeout=(3.05, 15)
            )
            if response.status_code in [200, 201]:
                logger.info(f"✅ Lista Evolution enviada a {clean_number}")
                return True
            logger.error(f"❌ Error Evolution sendList: {response.text[:300]}")
            return False
        except Exception as e:
            logger.error(f"❌ Excepción Evolution sendList: {e}")
            return False

    @classmethod
    def send_reaction(cls, instance_name: str, number: str, message_id: str, emoji: str = "👍"):
        """Envía una reacción (emoji) a un mensaje específico.

        Args:
            instance_name: Nombre de la instancia Evolution
            number: Número de teléfono del destinatario
            message_id: ID del mensaje al que reaccionar (se obtiene del webhook)
            emoji: Emoji a enviar (👍, ❤️, 😂, etc.)
        """
        return whatsapp_circuit_breaker.call(
            cls._send_reaction_internal, instance_name, number, message_id, emoji
        )

    @classmethod
    def _send_reaction_internal(cls, instance_name: str, number: str, message_id: str, emoji: str):
        cls._ensure_instance(instance_name)
        url = f"{cls._get_base_url()}/message/sendReaction/{instance_name}"
        clean_number = cls._clean_number(number)

        payload = {
            "number": clean_number,
            "reactionMessage": {
                "key": {"id": message_id, "fromMe": False},
                "reaction": emoji,
            },
        }

        try:
            session = cls._get_session()
            response = session.post(
                url, json=payload, headers=cls._get_headers(), timeout=(3.05, 10)
            )
            if response.status_code in [200, 201]:
                logger.info(f"✅ Reacción Evolution enviada a {clean_number}")
                return True
            logger.error(f"❌ Error Evolution sendReaction: {response.text[:300]}")
            return False
        except Exception as e:
            logger.error(f"❌ Excepción Evolution sendReaction: {e}")
            return False

    @classmethod
    def send_location(
        cls,
        instance_name: str,
        number: str,
        name: str,
        address: str,
        latitude: float,
        longitude: float,
    ):
        """Envía una ubicación.

        Args:
            instance_name: Nombre de la instancia Evolution
            number: Número de teléfono del destinatario
            name: Nombre del lugar
            address: Dirección del lugar
            latitude: Latitud
            longitude: Longitud
        """
        return whatsapp_circuit_breaker.call(
            cls._send_location_internal, instance_name, number, name, address, latitude, longitude
        )

    @classmethod
    def _send_location_internal(
        cls,
        instance_name: str,
        number: str,
        name: str,
        address: str,
        latitude: float,
        longitude: float,
    ):
        cls._ensure_instance(instance_name)
        url = f"{cls._get_base_url()}/message/sendLocation/{instance_name}"
        clean_number = cls._clean_number(number)

        payload = {
            "number": clean_number,
            "options": {"delay": 1200},
            "locationMessage": {
                "name": name,
                "address": address,
                "latitude": latitude,
                "longitude": longitude,
            },
        }

        try:
            session = cls._get_session()
            response = session.post(
                url, json=payload, headers=cls._get_headers(), timeout=(3.05, 10)
            )
            if response.status_code in [200, 201]:
                logger.info(f"✅ Ubicación Evolution enviada a {clean_number}")
                return True
            logger.error(f"❌ Error Evolution sendLocation: {response.text[:300]}")
            return False
        except Exception as e:
            logger.error(f"❌ Excepción Evolution sendLocation: {e}")
            return False

    @classmethod
    def send_contact(
        cls,
        instance_name: str,
        number: str,
        contact_name: str,
        phone: str,
        email: str = "",
        organization: str = "",
    ):
        """Envía un contacto (tarjeta de contacto).

        Args:
            instance_name: Nombre de la instancia Evolution
            number: Número de teléfono del destinatario
            contact_name: Nombre del contacto
            phone: Teléfono del contacto
            email: Email del contacto (opcional)
            organization: Organización del contacto (opcional)
        """
        return whatsapp_circuit_breaker.call(
            cls._send_contact_internal,
            instance_name,
            number,
            contact_name,
            phone,
            email,
            organization,
        )

    @classmethod
    def _send_contact_internal(
        cls,
        instance_name: str,
        number: str,
        contact_name: str,
        phone: str,
        email: str = "",
        organization: str = "",
    ):
        cls._ensure_instance(instance_name)
        url = f"{cls._get_base_url()}/message/sendContact/{instance_name}"
        clean_number = cls._clean_number(number)
        clean_contact_phone = cls._clean_number(phone)

        payload = {
            "number": clean_number,
            "options": {"delay": 1200},
            "contactMessage": [
                {
                    "displayName": contact_name,
                    "phone": clean_contact_phone,
                    "email": email or "",
                    "organization": organization or "",
                }
            ],
        }

        try:
            session = cls._get_session()
            response = session.post(
                url, json=payload, headers=cls._get_headers(), timeout=(3.05, 10)
            )
            if response.status_code in [200, 201]:
                logger.info(f"✅ Contacto Evolution enviado a {clean_number}")
                return True
            logger.error(f"❌ Error Evolution sendContact: {response.text[:300]}")
            return False
        except Exception as e:
            logger.error(f"❌ Excepción Evolution sendContact: {e}")
            return False

    @classmethod
    def send_sticker(cls, instance_name: str, number: str, sticker_url: str):
        """Envía un sticker.

        Args:
            instance_name: Nombre de la instancia Evolution
            number: Número de teléfono del destinatario
            sticker_url: URL de la imagen del sticker (debe ser PNG/WebP)
        """
        return whatsapp_circuit_breaker.call(
            cls._send_sticker_internal, instance_name, number, sticker_url
        )

    @classmethod
    def _send_sticker_internal(cls, instance_name: str, number: str, sticker_url: str):
        cls._ensure_instance(instance_name)
        url = f"{cls._get_base_url()}/message/sendSticker/{instance_name}"
        clean_number = cls._clean_number(number)

        payload = {
            "number": clean_number,
            "stickerMessage": {"url": sticker_url},
        }

        try:
            session = cls._get_session()
            response = session.post(
                url, json=payload, headers=cls._get_headers(), timeout=(3.05, 15)
            )
            if response.status_code in [200, 201]:
                logger.info(f"✅ Sticker Evolution enviado a {clean_number}")
                return True
            logger.error(f"❌ Error Evolution sendSticker: {response.text[:300]}")
            return False
        except Exception as e:
            logger.error(f"❌ Excepción Evolution sendSticker: {e}")
            return False

    # ==========================================================================
    # WEBHOOK & INSTANCE MANAGEMENT
    # ==========================================================================

    @classmethod
    def set_webhook(cls, instance_name: str, webhook_url: str, events: list[str] = None):
        """Configura el webhook de una instancia Evolution para recibir eventos.

        Args:
            instance_name: Nombre de la instancia
            webhook_url: URL pública donde Evolution enviará los eventos
            events: Lista de eventos a escuchar. Por defecto: ["MESSAGES_UPSERT", "MESSAGES_UPDATE", "SEND_MESSAGE"]
        """
        if events is None:
            events = ["MESSAGES_UPSERT", "MESSAGES_UPDATE", "SEND_MESSAGE"]

        url = f"{cls._get_base_url()}/webhook/set/{instance_name}"
        payload = {
            "webhook": {"url": webhook_url, "events": events},
            "enabled": True,
        }

        try:
            session = cls._get_session()
            response = session.post(
                url, json=payload, headers=cls._get_headers(), timeout=(3.05, 10)
            )
            if response.status_code in [200, 201]:
                logger.info(
                    f"✅ Webhook configurado para instancia '{instance_name}' -> {webhook_url}"
                )
                return True
            logger.error(f"❌ Error configurando webhook: {response.text[:300]}")
            return False
        except Exception as e:
            logger.error(f"❌ Excepción configurando webhook: {e}")
            return False

    @classmethod
    def get_webhook(cls, instance_name: str) -> dict | None:
        """Obtiene la configuración actual del webhook de una instancia."""
        url = f"{cls._get_base_url()}/webhook/find/{instance_name}"
        try:
            session = cls._get_session()
            response = session.get(url, headers=cls._get_headers(), timeout=(3.05, 10))
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            logger.error(f"❌ Error obteniendo webhook: {e}")
            return None

    @classmethod
    def set_webhook_global(cls, webhook_url: str, events: list[str] = None):
        """Configura el webhook global para todas las instancias nuevas."""
        if events is None:
            events = ["MESSAGES_UPSERT", "MESSAGES_UPDATE", "SEND_MESSAGE"]

        url = f"{cls._get_base_url()}/webhook"
        payload = {
            "webhook": {"url": webhook_url, "events": events},
            "enabled": True,
        }

        try:
            session = cls._get_session()
            response = session.post(
                url, json=payload, headers=cls._get_headers(), timeout=(3.05, 10)
            )
            if response.status_code in [200, 201]:
                logger.info(f"✅ Webhook global configurado -> {webhook_url}")
                return True
            logger.error(f"❌ Error configurando webhook global: {response.text[:300]}")
            return False
        except Exception as e:
            logger.error(f"❌ Excepción configurando webhook global: {e}")
            return False

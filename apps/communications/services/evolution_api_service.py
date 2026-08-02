import logging
import os
from urllib.parse import urlparse

import requests
from django.conf import settings
from django.core.cache import cache
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

from apps.common.services.circuit_breaker import whatsapp_circuit_breaker

logger = logging.getLogger(__name__)

# Timeouts de red para Evolution API (P3-66). Conectividad/lectura en segundos.
_TIMEOUT_CONNECT = 5
_TIMEOUT_READ_QUICK = 10
_TIMEOUT_READ_DEFAULT = 15
_TIMEOUT_READ_MEDIA = 30


class EvolutionService:
    """
    Servicio avanzado para interactuar con Evolution API v2.
    Permite el manejo de mÃºltiples instancias (una por agencia) y el envÃ­o de media.
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

    _cached_session: requests.Session | None = None

    @classmethod
    def _get_session(cls) -> requests.Session:
        if cls._cached_session is None:
            session = requests.Session()
            retries = Retry(
                total=3,
                backoff_factor=0.3,
                status_forcelist=[500, 502, 503, 504],
                raise_on_status=False,
            )
            session.mount("http://", HTTPAdapter(max_retries=retries))
            session.mount("https://", HTTPAdapter(max_retries=retries))
            cls._cached_session = session
        return cls._cached_session

    @classmethod
    def _build_webhook_payload(cls, instance_name: str) -> dict | None:
        """Construye el payload de webhook para Evolution API.

        En Docker, evolution -> web container via red interna.
        En produccion, EVOLUTION_WEBHOOK_URL debe configurarse con la URL publica.
        """
        try:
            from django.conf import settings as dj_settings
            from django.urls import reverse

            path = reverse("crm:evolution_webhook")
            webhook_url = getattr(dj_settings, "EVOLUTION_WEBHOOK_URL", None)
            if not webhook_url:
                # Resolver el host de forma dinámica: env → request host → fallback Docker (P3-67)
                webhook_host = os.getenv("WEBHOOK_HOST", None)
                if not webhook_host:
                    webhook_host = cls._resolve_public_host()
                if webhook_host:
                    webhook_url = webhook_host.rstrip("/") + path
                else:
                    webhook_url = "http://web:8000" + path
        except Exception:
            return None
        return {
            "enabled": True,
            "url": webhook_url,
            "events": [
                "MESSAGES_UPSERT",
                "MESSAGES_UPDATE",
                "SEND_MESSAGE",
                "QRCODE_UPDATED",
                "CONNECTION_UPDATE",
            ],
            "webhookByEvents": False,
            "webhookBase64": False,
        }

    @classmethod
    def _resolve_public_host(cls) -> str | None:
        """Resuelve el host público del webhook sin hardcodear (P3-67).

        Orden: PUBLIC_BASE_URL → DJANGO_ALLOWED_HOSTS[0] → None (fallback Docker).
        """
        public_base = os.getenv("PUBLIC_BASE_URL", None) or getattr(
            settings, "PUBLIC_BASE_URL", None
        )
        if public_base:
            return public_base
        allowed = getattr(settings, "ALLOWED_HOSTS", None) or []
        for host in allowed:
            if host and not host.startswith(".") and "*" not in host and host != "localhost":
                return f"http://{host}"
        return None

    @classmethod
    def create_instance(cls, instance_name: str):
        """Crea una nueva instancia en Evolution API v2."""
        url = f"{cls._get_base_url()}/instance/create"
        webhook_cfg = cls._build_webhook_payload(instance_name)
        payload = {
            "instanceName": instance_name,
            "token": settings.EVOLUTION_INSTANCE_TOKEN,
            "qrcode": True,
            "integration": "WHATSAPP-BAILEYS",
        }
        if webhook_cfg:
            payload["webhook"] = webhook_cfg
        try:
            session = cls._get_session()
            response = session.post(
                url,
                json=payload,
                headers=cls._get_headers(),
                timeout=(_TIMEOUT_CONNECT, _TIMEOUT_READ_DEFAULT),  # connect, read
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
                timeout=(_TIMEOUT_CONNECT, _TIMEOUT_READ_QUICK),  # connect, read
            )
            if response.status_code == 200:
                data = response.json()
                state = data.get("instance", {}).get("state")
                logger.info(f"ðŸ” Evolution API: Instance '{instance_name}' state is '{state}'")
                return state
            else:
                logger.warning(
                    f"âš ï¸ Evolution API get_instance_state returned {response.status_code}: {response.text}"
                )
        except Exception as e:
            logger.error(f"âŒ Evolution API get_instance_state error: {e}")
            pass
        return "disconnected"

    @classmethod
    def get_connection_status(cls, instance_name: str):
        """Mantiene compatibilidad devolviendo True solo si estÃ¡ 'open'."""
        return cls.get_instance_state(instance_name) == "open"

    @classmethod
    def get_connection_qr_base64(cls, instance_name: str, timeout: int = 12):
        """Llama a Evolution /instance/connect y devuelve el QR en base64.

        Devuelve None si no hay QR disponible (versiÃ³n exhaustiva de la API).

        Ãštil como fallback para garantizar que el frontend tenga SIEMPRE un data:image
        en cache, evitando el iframe roto (404) del Evolution Manager UI proxy.
        """
        url = f"{cls._get_base_url()}/instance/connect/{instance_name}"
        cache_key = f"evo_qr:{instance_name}"

        # Si ya estÃ¡ conectado a WhatsApp, no hay QR que mostrar.
        if cls.get_instance_state(instance_name) == "open":
            cache.delete(cache_key)
            return None

        try:
            session = cls._get_session()
            headers = cls._get_headers()
            headers.pop("Content-Type", None)
            response = session.get(url, headers=headers, timeout=(_TIMEOUT_CONNECT, timeout))

            if response.status_code == 404:
                logger.info(f"Instancia '{instance_name}' no existe, creÃ¡ndola...")
                cls.create_instance(instance_name)
                response = session.get(url, headers=headers, timeout=(_TIMEOUT_CONNECT, timeout))

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
                    logger.info(f"QR fetched sincronamente para {instance_name}")
                    return raw
                else:
                    logger.debug(
                        f"Evolution devolviÃ³ 200 OK sin base64 para {instance_name}: count={data.get('count')}"
                    )
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
                timeout=(_TIMEOUT_CONNECT, _TIMEOUT_READ_DEFAULT),  # connect, read
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
        """Retorna la URL de la imagen QR o el Manager UI."""
        try:
            from django.urls import reverse

            return reverse("evolution_manager_root", kwargs={"instance_name": instance_name})
        except Exception:
            return f"/manager/qr/{instance_name}/"

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
                timeout=(_TIMEOUT_CONNECT, _TIMEOUT_READ_DEFAULT),  # connect, read
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
    def _check_and_increment_rate_limit(cls, instance_name: str, max_per_hour: int = 30) -> bool:
        """Verifica e incrementa el contador de mensajes salientes para la instancia.

        Límite configurable por EVOLUTION_MAX_MSG_PER_HOUR en settings (default: 30 msgs/hora).
        Protege las líneas de las agencias contra detecciones de spam y bans de Meta.

        Returns:
            bool: True si el envío está permitido, False si superó el límite.
        """
        limit = getattr(settings, "EVOLUTION_MAX_MSG_PER_HOUR", max_per_hour)
        key = f"evo_rate:{instance_name}"
        try:
            count = cache.get(key, 0)
            if count >= limit:
                logger.warning(
                    f"⚠️ [EvolutionRateLimit] Instancia '{instance_name}' superó el límite "
                    f"de {limit} msgs/hora ({count}/{limit}). Mensaje bloqueado para prevenir ban."
                )
                return False
            cache.set(key, count + 1, timeout=3600)
            return True
        except Exception as e:
            logger.warning(f"⚠️ [EvolutionRateLimit] Error consultando caché: {e}")
            return True

    @classmethod
    def send_text(cls, instance_name: str, number: str, text: str):
        """EnvÃ­a un mensaje de texto simple con auto-provisioning y circuit breaker."""
        return whatsapp_circuit_breaker.call(cls._send_text_internal, instance_name, number, text)

    @classmethod
    def _send_text_internal(cls, instance_name: str, number: str, text: str):
        """Internal send implementation protected by circuit breaker and rate limiter."""
        if not cls._check_and_increment_rate_limit(instance_name):
            return False

        cls._ensure_instance(instance_name)

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
                timeout=(_TIMEOUT_CONNECT, _TIMEOUT_READ_DEFAULT),  # connect, read
            )
            if response.status_code in [200, 201]:
                logger.info(f"âœ… WhatsApp (Evolution) enviado a {clean_number}")
                return True
            logger.error(f"âŒ Error Evolution sendText: {response.text}")
            return False
        except Exception as e:
            logger.error(f"âŒ ExcepciÃ³n Evolution sendText: {e}")
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
        """EnvÃ­a un archivo (PDF, Imagen) vÃ­a Evolution API con circuit breaker."""
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
        """Internal media send implementation protected by circuit breaker and rate limiter."""
        if not cls._check_and_increment_rate_limit(instance_name):
            return False

        cls._ensure_instance(instance_name)

        url = f"{cls._get_base_url()}/message/sendMedia/{instance_name}"
        clean_number = "".join(filter(str.isdigit, str(number)))

        mimetype = "application/pdf"
        if media_url.lower().endswith((".png", ".jpg", ".jpeg")):
            mimetype = "image/jpeg"

        cls._validate_media_url(media_url)

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
                timeout=(
                    _TIMEOUT_CONNECT,
                    _TIMEOUT_READ_MEDIA,
                ),  # connect, read (media takes longer)
            )
            if response.status_code in [200, 201]:
                logger.info(f"âœ… Media Evolution enviado a {clean_number}")
                return True
            logger.error(f"âŒ Error Evolution sendMedia: {response.text}")
            return False
        except Exception as e:
            logger.error(f"âŒ ExcepciÃ³n Evolution sendMedia: {e}")
            return False

    @classmethod
    def delete_instance(cls, instance_name: str):
        """Elimina/Desconecta una instancia de Evolution API."""
        url = f"{cls._get_base_url()}/instance/delete/{instance_name}"
        try:
            session = cls._get_session()
            response = session.delete(
                url, headers=cls._get_headers(), timeout=(_TIMEOUT_CONNECT, _TIMEOUT_READ_DEFAULT)
            )
            return response.status_code in [200, 201, 204]
        except Exception as e:
            logger.error(f"âŒ Error eliminando instancia: {e}")
            return False

    # ==========================================================================
    # RICH MESSAGE TYPES (Buttons, Lists, Reactions, Location, Contact, Sticker)
    # ==========================================================================

    @classmethod
    def _validate_media_url(cls, url: str) -> None:
        """Valida que media_url no apunte a recursos internos (SSRF prevention)."""
        parsed = urlparse(url)
        if parsed.scheme in ("file", "local"):
            raise ValueError(f"URL scheme no permitido: {parsed.scheme}")
        host = parsed.hostname or ""
        if host in ("localhost", "127.0.0.1", "0.0.0.0", "::1", "web", "redis", "db", "evolution"):  # noqa: S104
            raise ValueError(f"Host interno no permitido: {host}")
        if host.startswith("10.") or host.startswith("172.") or host.startswith("192.168."):
            raise ValueError(f"IP privada no permitida: {host}")

    @classmethod
    def _ensure_instance(cls, instance_name: str):
        """Ensure instance exists and is connected, create if needed.

        Uses cache-based lock to prevent TOCTOU race when multiple workers
        try to create the same instance simultaneously.
        """
        if cls.get_connection_status(instance_name):
            return

        lock_key = f"evo_create_instance:{instance_name}"
        if not cache.add(lock_key, True, 30):
            logger.info(f"CreaciÃ³n de instancia '{instance_name}' ya en progreso por otro worker")
            return

        try:
            logger.info(f"Instancia '{instance_name}' no conectada. Intentando crear...")
            cls.create_instance(instance_name)
        finally:
            cache.delete(lock_key)

    @classmethod
    def _clean_number(cls, number: str) -> str:
        return "".join(filter(str.isdigit, str(number)))

    @classmethod
    def send_buttons(cls, instance_name: str, number: str, text: str, buttons: list[dict]):
        """EnvÃ­a un mensaje con botones interactivos.

        Args:
            instance_name: Nombre de la instancia Evolution
            number: NÃºmero de telÃ©fono del destinatario
            text: Texto del mensaje
            buttons: Lista de botones. Cada botÃ³n: {"text": "Etiqueta", "id": "valor"}
                Ejemplo: [{"text": "SÃ­, quiero", "id": "confirmar"}, {"text": "No, gracias", "id": "rechazar"}]
                MÃ¡ximo 3 botones.
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
                    {"text": b.get("text", "OpciÃ³n"), "id": b.get("id", str(i))}
                    for i, b in enumerate(buttons[:3])
                ],
            },
        }

        try:
            session = cls._get_session()
            response = session.post(
                url,
                json=payload,
                headers=cls._get_headers(),
                timeout=(_TIMEOUT_CONNECT, _TIMEOUT_READ_MEDIA),
            )
            if response.status_code in [200, 201]:
                logger.info(f"âœ… Botones Evolution enviados a {clean_number}")
                return True
            logger.error(f"âŒ Error Evolution sendButtons: {response.text[:300]}")
            return False
        except Exception as e:
            logger.error(f"âŒ ExcepciÃ³n Evolution sendButtons: {e}")
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
        """EnvÃ­a un mensaje con lista de opciones seleccionables.

        Args:
            instance_name: Nombre de la instancia Evolution
            number: NÃºmero de telÃ©fono del destinatario
            text: Texto del mensaje (footer opcional)
            title: TÃ­tulo de la lista
            button_text: Texto del botÃ³n que abre la lista
            sections: Lista de secciones. Cada secciÃ³n:
                {"title": "TÃ­tulo secciÃ³n", "rows": [{"title": "OpciÃ³n", "description": "DescripciÃ³n", "id": "valor"}]}
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
                url,
                json=payload,
                headers=cls._get_headers(),
                timeout=(_TIMEOUT_CONNECT, _TIMEOUT_READ_MEDIA),
            )
            if response.status_code in [200, 201]:
                logger.info(f"âœ… Lista Evolution enviada a {clean_number}")
                return True
            logger.error(f"âŒ Error Evolution sendList: {response.text[:300]}")
            return False
        except Exception as e:
            logger.error(f"âŒ ExcepciÃ³n Evolution sendList: {e}")
            return False

    @classmethod
    def send_reaction(cls, instance_name: str, number: str, message_id: str, emoji: str = "ðŸ‘"):
        """EnvÃ­a una reacciÃ³n (emoji) a un mensaje especÃ­fico.

        Args:
            instance_name: Nombre de la instancia Evolution
            number: NÃºmero de telÃ©fono del destinatario
            message_id: ID del mensaje al que reaccionar (se obtiene del webhook)
            emoji: Emoji a enviar (ðŸ‘, â¤ï¸, ðŸ˜‚, etc.)
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
                url,
                json=payload,
                headers=cls._get_headers(),
                timeout=(_TIMEOUT_CONNECT, _TIMEOUT_READ_DEFAULT),
            )
            if response.status_code in [200, 201]:
                logger.info(f"âœ… ReacciÃ³n Evolution enviada a {clean_number}")
                return True
            logger.error(f"âŒ Error Evolution sendReaction: {response.text[:300]}")
            return False
        except Exception as e:
            logger.error(f"âŒ ExcepciÃ³n Evolution sendReaction: {e}")
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
        """EnvÃ­a una ubicaciÃ³n.

        Args:
            instance_name: Nombre de la instancia Evolution
            number: NÃºmero de telÃ©fono del destinatario
            name: Nombre del lugar
            address: DirecciÃ³n del lugar
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
                url,
                json=payload,
                headers=cls._get_headers(),
                timeout=(_TIMEOUT_CONNECT, _TIMEOUT_READ_DEFAULT),
            )
            if response.status_code in [200, 201]:
                logger.info(f"âœ… UbicaciÃ³n Evolution enviada a {clean_number}")
                return True
            logger.error(f"âŒ Error Evolution sendLocation: {response.text[:300]}")
            return False
        except Exception as e:
            logger.error(f"âŒ ExcepciÃ³n Evolution sendLocation: {e}")
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
        """EnvÃ­a un contacto (tarjeta de contacto).

        Args:
            instance_name: Nombre de la instancia Evolution
            number: NÃºmero de telÃ©fono del destinatario
            contact_name: Nombre del contacto
            phone: TelÃ©fono del contacto
            email: Email del contacto (opcional)
            organization: OrganizaciÃ³n del contacto (opcional)
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
                url,
                json=payload,
                headers=cls._get_headers(),
                timeout=(_TIMEOUT_CONNECT, _TIMEOUT_READ_DEFAULT),
            )
            if response.status_code in [200, 201]:
                logger.info(f"âœ… Contacto Evolution enviado a {clean_number}")
                return True
            logger.error(f"âŒ Error Evolution sendContact: {response.text[:300]}")
            return False
        except Exception as e:
            logger.error(f"âŒ ExcepciÃ³n Evolution sendContact: {e}")
            return False

    @classmethod
    def send_sticker(cls, instance_name: str, number: str, sticker_url: str):
        """EnvÃ­a un sticker.

        Args:
            instance_name: Nombre de la instancia Evolution
            number: NÃºmero de telÃ©fono del destinatario
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
                url,
                json=payload,
                headers=cls._get_headers(),
                timeout=(_TIMEOUT_CONNECT, _TIMEOUT_READ_MEDIA),
            )
            if response.status_code in [200, 201]:
                logger.info(f"âœ… Sticker Evolution enviado a {clean_number}")
                return True
            logger.error(f"âŒ Error Evolution sendSticker: {response.text[:300]}")
            return False
        except Exception as e:
            logger.error(f"âŒ ExcepciÃ³n Evolution sendSticker: {e}")
            return False

    # ==========================================================================
    # WEBHOOK & INSTANCE MANAGEMENT
    # ==========================================================================

    @classmethod
    def set_webhook(cls, instance_name: str, webhook_url: str, events: list[str] = None):
        """Configura el webhook de una instancia Evolution para recibir eventos.

        Args:
            instance_name: Nombre de la instancia
            webhook_url: URL pÃºblica donde Evolution enviarÃ¡ los eventos
            events: Lista de eventos a escuchar. Por defecto: ["MESSAGES_UPSERT", "MESSAGES_UPDATE", "SEND_MESSAGE", "QRCODE_UPDATED", "CONNECTION_UPDATE"]
        """
        if events is None:
            events = [
                "MESSAGES_UPSERT",
                "MESSAGES_UPDATE",
                "SEND_MESSAGE",
                "QRCODE_UPDATED",
                "CONNECTION_UPDATE",
            ]

        url = f"{cls._get_base_url()}/webhook/set/{instance_name}"
        payload = {
            "webhook": {
                "enabled": True,
                "url": webhook_url,
                "events": events,
                "webhookByEvents": False,
                "webhookBase64": False,
            },
        }

        try:
            session = cls._get_session()
            response = session.post(
                url,
                json=payload,
                headers=cls._get_headers(),
                timeout=(_TIMEOUT_CONNECT, _TIMEOUT_READ_DEFAULT),
            )
            if response.status_code in [200, 201]:
                logger.info(
                    f"âœ… Webhook configurado para instancia '{instance_name}' -> {webhook_url}"
                )
                return True
            logger.error(f"âŒ Error configurando webhook: {response.text[:300]}")
            return False
        except Exception as e:
            logger.error(f"âŒ ExcepciÃ³n configurando webhook: {e}")
            return False

    @classmethod
    def get_webhook(cls, instance_name: str) -> dict | None:
        """Obtiene la configuraciÃ³n actual del webhook de una instancia."""
        url = f"{cls._get_base_url()}/webhook/find/{instance_name}"
        try:
            session = cls._get_session()
            response = session.get(
                url, headers=cls._get_headers(), timeout=(_TIMEOUT_CONNECT, _TIMEOUT_READ_DEFAULT)
            )
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            logger.error(f"âŒ Error obteniendo webhook: {e}")
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
                url,
                json=payload,
                headers=cls._get_headers(),
                timeout=(_TIMEOUT_CONNECT, _TIMEOUT_READ_DEFAULT),
            )
            if response.status_code in [200, 201]:
                logger.info(f"âœ… Webhook global configurado -> {webhook_url}")
                return True
            logger.error(f"âŒ Error configurando webhook global: {response.text[:300]}")
            return False
        except Exception as e:
            logger.error(f"âŒ ExcepciÃ³n configurando webhook global: {e}")
            return False

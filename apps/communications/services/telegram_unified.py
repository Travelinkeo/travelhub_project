"""
Telegram Unified Service
Consolidated service for all Telegram operations:
- Message sending (Text/HTML/Markdown)
- Document/File sending (Local path, URL, File ID)
- File retrieval (get_file_url)
- Async/Sync wrappers for alerts and files
- Storage service (Channel as unlimited storage)
- Logo/Image upload utilities

Multitenant Isolation (v2):
  Token/chat-id resolution uses a strict priority chain via _resolve_telegram_config()
  to guarantee that each agency uses its own credentials - never a global fallback
  when an agency object is passed in.
"""

import asyncio
import logging
import os

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


# ============================================================================
# SECTION 0: MULTITENANT CONFIG RESOLVER
# ============================================================================


def _resolve_telegram_config(agencia=None, purpose: str = "notify") -> dict:
    """Resuelve el token y chat_id correctos para el contexto dado.

    Jerarquia de resolucion (de mas especifico a mas general):
      1. Campos dedicados del modelo AgenciaConfiguracion (EncryptedCharField)
         - agencia.telegram_bot_token / agencia.telegram_chat_id
      2. JSON blob configuracion_api (compatibilidad con datos legacy)
         - agencia.configuracion_api["TELEGRAM_BOT_TOKEN"] etc.
      3. settings globales - SOLO si NO se pasa una agencia (alertas de sistema)

    Args:
        agencia: Instancia de Agencia, o None para contexto de sistema.
        purpose:  "notify"  - chat de notificaciones del staff (telegram_chat_id)
                  "storage" - canal de almacenamiento de archivos

    Returns:
        dict con claves "token" y "chat_id" (pueden ser None).
    """
    token = None
    chat_id = None

    if agencia is not None:
        cfg_api = getattr(agencia, "configuracion_api", {}) or {}

        # --- TOKEN ---
        # Prioridad 1: campo dedicado cifrado en AgenciaConfiguracion
        token = getattr(agencia, "telegram_bot_token", None)
        # Prioridad 2: JSON blob legacy
        if not token:
            token = cfg_api.get("TELEGRAM_BOT_TOKEN")

        if not token:
            agencia_str = getattr(agencia, "nombre", str(agencia))
            logger.warning(
                "[Telegram] Agencia '%s' no tiene TELEGRAM_BOT_TOKEN configurado. "
                "No se enviara con el token global para evitar cruce de tenants.",
                agencia_str,
            )
            return {"token": None, "chat_id": None}

        # --- CHAT ID (segun proposito) ---
        if purpose == "storage":
            # Canal de almacenamiento de archivos (PDFs, logos)
            chat_id = (
                getattr(agencia, "telegram_storage_channel_id", None)
                or cfg_api.get("TELEGRAM_STORAGE_CHANNEL_ID")
                or getattr(agencia, "telegram_chat_id", None)
                or cfg_api.get("TELEGRAM_CHANNEL_ID")
                or cfg_api.get("TELEGRAM_GROUP_ID")
            )
        else:
            # Canal de notificaciones del staff (proposito por defecto)
            chat_id = (
                getattr(agencia, "telegram_chat_id", None)
                or cfg_api.get("TELEGRAM_FINANZAS_CHAT_ID")
                or cfg_api.get("TELEGRAM_OPERACIONES_CHAT_ID")
                or cfg_api.get("TELEGRAM_CHANNEL_ID")
                or cfg_api.get("TELEGRAM_GROUP_ID")
            )

    else:
        # Sin agencia: contexto de sistema, se permite el settings global
        token = getattr(settings, "TELEGRAM_BOT_TOKEN", None)
        chat_id = getattr(settings, "TELEGRAM_GROUP_ID", None) or getattr(
            settings, "TELEGRAM_CHANNEL_ID", None
        )

    return {"token": token, "chat_id": chat_id}


# ============================================================================
# SECTION 1: CORE MESSAGING (HTTP API)
# ============================================================================


class TelegramNotificationService:
    """
    Servicio unificado para enviar notificaciones y archivos a Telegram.
    Centraliza la logica de envio para Boletos, Facturas y otros documentos.

    Multitenant: cada agencia usa sus propias credenciales.
    """

    @staticmethod
    def build_inline_keyboard(buttons_matrix: list) -> str:
        """Construye la estructura de teclado Inline (InlineKeyboardMarkup) serializada en JSON.

        Args:
            buttons_matrix: Lista de filas de botones.
                Ejemplo:
                [
                    [{"text": "✅ Aprobar", "callback_data": "approve_123"}, {"text": "❌ Rechazar", "callback_data": "reject_123"}],
                    [{"text": "🌐 Ver en Web", "url": "https://travelhub.cc/sales/123"}]
                ]
        Returns:
            str: JSON string para el parámetro reply_markup de la API de Telegram.
        """
        import json

        return json.dumps({"inline_keyboard": buttons_matrix})

    @staticmethod
    def answer_callback_query(
        callback_query_id: str,
        text: str = "",
        show_alert: bool = False,
        agencia=None,
    ) -> bool:
        """Responde a un toque de botón inline (callback_query) para quitar el indicador de carga.

        Args:
            callback_query_id: ID de la interacción de Telegram.
            text: Mensaje flotante corto a mostrar en pantalla.
            show_alert: Si es True, muestra una alerta modal.
            agencia: Instancia de Agencia para resolver el bot token.
        """
        try:
            cfg = _resolve_telegram_config(agencia, purpose="notify")
            token = cfg["token"]
            if not token:
                return False

            url = f"https://api.telegram.org/bot{token}/answerCallbackQuery"
            payload = {
                "callback_query_id": callback_query_id,
                "text": text,
                "show_alert": show_alert,
            }
            response = requests.post(url, json=payload, timeout=10)
            return response.status_code == 200
        except Exception as e:
            logger.error("[Telegram] Error en answer_callback_query: %s", e)
            return False

    @staticmethod
    def send_message(
        message: str,
        chat_id: str = None,
        parse_mode: str = "HTML",
        agencia=None,
        reply_markup: str = None,
        **kwargs,
    ) -> bool:
        """Envia un mensaje de texto simple al canal de la agencia (o al chat_id explicito)."""
        try:
            cfg = _resolve_telegram_config(agencia, purpose="notify")
            token = cfg["token"]
            chat = chat_id or cfg["chat_id"]

            if not token or not chat:
                agencia_str = getattr(agencia, "nombre", str(agencia)) if agencia else "sistema"
                logger.warning(
                    "[Telegram] send_message: Config incompleta para '%s'. Token=%s, Chat=%s",
                    agencia_str,
                    bool(token),
                    chat,
                )
                return False

            url = f"https://api.telegram.org/bot{token}/sendMessage"
            payload = {"chat_id": chat, "text": message, "parse_mode": parse_mode}
            if reply_markup:
                payload["reply_markup"] = reply_markup
            if kwargs:
                payload.update(kwargs)
            response = requests.post(url, data=payload, timeout=30)
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error("[Telegram] Error sending message: %s", e)
            return False

    @staticmethod
    def send_document(file_path: str, caption: str = None, chat_id: str = None, agencia=None):
        """Envia un documento (PDF, etc.) a Telegram via Path Local, URL, o File ID.

        Usa el canal de storage de la agencia si no se especifica chat_id.
        Retorna el file_id si el envio fue exitoso, True si no hay file_id, False si fallo.
        """
        try:
            cfg = _resolve_telegram_config(agencia, purpose="storage")
            token = cfg["token"]
            chat = chat_id or cfg["chat_id"]

            if not token or not chat:
                agencia_str = getattr(agencia, "nombre", str(agencia)) if agencia else "sistema"
                logger.warning(
                    "[Telegram] send_document: Config incompleta para '%s'. Token=%s, Chat=%s",
                    agencia_str,
                    bool(token),
                    chat,
                )
                return False

            url_api = f"https://api.telegram.org/bot{token}/sendDocument"

            if file_path.startswith("http"):
                logger.info("[Telegram] Enviando documento via URL: %s", file_path)
                data = {
                    "chat_id": chat,
                    "document": file_path,
                    "caption": caption,
                    "parse_mode": "HTML",
                }
                response = requests.post(url_api, data=data, timeout=60)

            elif os.path.exists(file_path):
                with open(file_path, "rb") as f:
                    files = {"document": f}
                    data = {"chat_id": chat}
                    if caption:
                        data["caption"] = caption
                        data["parse_mode"] = "HTML"
                    response = requests.post(url_api, data=data, files=files, timeout=60)

            else:
                logger.info("[Telegram] Enviando documento via File ID: %s", file_path)
                data = {
                    "chat_id": chat,
                    "document": file_path,
                    "caption": caption,
                    "parse_mode": "HTML",
                }
                response = requests.post(url_api, data=data, timeout=60)

            if response.status_code != 200:
                logger.error("[Telegram] API Error: %s", response.text)
                response.raise_for_status()

            try:
                resp_json = response.json()
                if resp_json.get("ok"):
                    document = resp_json["result"].get("document")
                    file_id = document.get("file_id") if document else None
                    if file_id:
                        logger.info("[Telegram] Documento enviado. File ID: %s", file_id)
                        return file_id
            except Exception as e_json:
                logger.warning("[Telegram] No se pudo extraer file_id: %s", e_json)

            return True

        except Exception as e:
            logger.error("[Telegram] Error sending document: %s", e)
            return False

    @staticmethod
    def get_file_url(file_id: str, agencia=None):
        """Obtiene la URL temporal de descarga de un archivo de Telegram (~1h de validez)."""
        try:
            cfg = _resolve_telegram_config(agencia, purpose="notify")
            token = cfg["token"]

            if not token:
                agencia_str = getattr(agencia, "nombre", str(agencia)) if agencia else "sistema"
                logger.warning("[Telegram] get_file_url: Sin token para '%s'", agencia_str)
                return None

            url_api = f"https://api.telegram.org/bot{token}/getFile"
            response = requests.post(url_api, data={"file_id": file_id}, timeout=30)

            if response.status_code == 200:
                result = response.json().get("result", {})
                file_path_remote = result.get("file_path")
                if file_path_remote:
                    return f"https://api.telegram.org/file/bot{token}/{file_path_remote}"

            logger.error("[Telegram] Error getting file info: %s", response.text)
            return None

        except Exception as e:
            logger.error("[Telegram] Error resolving file URL: %s", e)
            return None


def enviar_alerta_telegram(mensaje: str, chat_id: str = None, agencia=None) -> bool:
    """Funcion shim para enviar alertas rapidas a Telegram."""
    success = TelegramNotificationService.send_message(mensaje, chat_id=chat_id, agencia=agencia)
    if success:
        logger.info("[Telegram] Alert sent successfully.")
    else:
        logger.error("[Telegram] Failed to send alert.")
    return success


# ============================================================================
# SECTION 2: ASYNC/SYNC WRAPPERS (python-telegram-bot)
# ============================================================================

try:
    from telegram import Bot

    async def send_telegram_alert(
        message: str, token: str = None, target_chat_id: str = None
    ) -> bool:
        """
        Envia una alerta al Grupo Configurado (o al Admin si no hay grupo).
        Para uso de sistema/plataforma (sin agencia especifica).
        """
        token = token or os.getenv("TELEGRAM_BOT_TOKEN")
        if not target_chat_id:
            admin_id = os.getenv("TELEGRAM_ADMIN_ID")
            group_id = os.getenv("TELEGRAM_GROUP_ID")
            target_chat_id = group_id if group_id else admin_id

        if not token or not target_chat_id:
            logger.warning("[Telegram] Config incompleto (Falta Token o Target ID).")
            return False

        try:
            bot = Bot(token=token)
            await bot.send_message(chat_id=target_chat_id, text=message, parse_mode="HTML")
            return True
        except Exception as e:
            logger.error("[Telegram] Error enviando alerta async: %s", e)
            return False

    def send_telegram_alert_sync(message: str, token: str = None, target_chat_id: str = None):
        """Wrapper sincrono para usar en contextos donde no se puede usar async/await."""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(send_telegram_alert(message, token, target_chat_id))
            loop.close()
        except Exception as e:
            logger.error("[Telegram] Error en wrapper sincrono: %s", e)

    async def send_telegram_file(
        file_path: str, caption: str = None, token: str = None, target_chat_id: str = None
    ) -> bool:
        """Envia un archivo (PDF, imagen, etc.) al Grupo o Admin."""
        token = token or os.getenv("TELEGRAM_BOT_TOKEN")
        if not target_chat_id:
            admin_id = os.getenv("TELEGRAM_ADMIN_ID")
            group_id = os.getenv("TELEGRAM_GROUP_ID")
            target_chat_id = group_id if group_id else admin_id

        if not token or not target_chat_id:
            return False

        try:
            if not os.path.exists(file_path):
                logger.error("[Telegram] Archivo no encontrado: %s", file_path)
                return False

            bot = Bot(token=token)
            with open(file_path, "rb") as f:
                await bot.send_document(
                    chat_id=target_chat_id,
                    document=f,
                    caption=caption,
                    parse_mode="HTML",
                    read_timeout=30,
                    write_timeout=30,
                    connect_timeout=30,
                )
            return True
        except Exception as e:
            logger.error("[Telegram] Error enviando archivo async: %s", e)
            return False

    def send_telegram_file_sync(
        file_path: str, caption: str = None, token: str = None, target_chat_id: str = None
    ):
        """Wrapper sincrono para enviar archivos."""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(send_telegram_file(file_path, caption, token, target_chat_id))
            loop.close()
        except Exception as e:
            logger.error("[Telegram] Error en wrapper sincrono (File): %s", e)

except ImportError:
    logger.warning("[Telegram] python-telegram-bot no instalado. Async wrappers deshabilitados.")

    async def send_telegram_alert(  # type: ignore[misc]
        message: str, token: str = None, target_chat_id: str = None
    ) -> bool:
        """send_telegram_alert."""
        logger.error("[Telegram] Async wrappers no disponibles: falta python-telegram-bot")
        return False

    def send_telegram_alert_sync(  # type: ignore[misc]
        message: str, token: str = None, target_chat_id: str = None
    ):
        """send_telegram_alert_sync."""
        logger.error("[Telegram] Async wrappers no disponibles: falta python-telegram-bot")

    async def send_telegram_file(  # type: ignore[misc]
        file_path: str, caption: str = None, token: str = None, target_chat_id: str = None
    ) -> bool:
        """send_telegram_file."""
        logger.error("[Telegram] Async wrappers no disponibles: falta python-telegram-bot")
        return False

    def send_telegram_file_sync(  # type: ignore[misc]
        file_path: str, caption: str = None, token: str = None, target_chat_id: str = None
    ):
        """send_telegram_file_sync."""
        logger.error("[Telegram] Async wrappers no disponibles: falta python-telegram-bot")


# ============================================================================
# SECTION 3: STORAGE SERVICE (Channel as Unlimited Storage)
# ============================================================================


class TelegramStorageService:
    """
    Servicio para usar un Canal de Telegram como almacenamiento de archivos.
    Sube archivos recuperando su file_id para referencias persistentes.

    Multitenant: requiere agencia para resolver el canal de storage correcto.
    Usado como backend por FileStorageService cuando R2 no esta disponible.
    """

    def __init__(self, agencia=None):
        """__init__.

        Args:
            agencia: Instancia de Agencia. Si es None, usa configuracion de sistema.
        """
        self._agencia = agencia
        cfg = _resolve_telegram_config(agencia, purpose="storage")
        self.bot_token = cfg["token"]
        self.storage_channel_id = cfg["chat_id"]

        if not self.bot_token:
            agencia_str = getattr(agencia, "nombre", "sistema") if agencia else "sistema"
            logger.warning(
                "[TelegramStorage] Sin token para '%s'. Servicio deshabilitado.", agencia_str
            )
        if not self.storage_channel_id:
            agencia_str = getattr(agencia, "nombre", "sistema") if agencia else "sistema"
            logger.warning("[TelegramStorage] Sin storage_channel_id para '%s'.", agencia_str)

    @property
    def is_configured(self) -> bool:
        """Retorna True si el servicio esta listo para operar."""
        return bool(self.bot_token and self.storage_channel_id)

    async def upload_file(
        self, file_path_or_buffer, filename: str = "documento.pdf", caption: str = None
    ):
        """Sube un archivo a Telegram y retorna su file_id (referencia persistente)."""
        if not self.is_configured:
            logger.error("[TelegramStorage] Servicio no configurado, no se puede subir.")
            return None

        try:
            from telegram import Bot  # noqa: PLC0415

            bot = Bot(token=self.bot_token)
            agencia_str = (
                getattr(self._agencia, "nombre", "sistema") if self._agencia else "sistema"
            )
            logger.info("[TelegramStorage] Subiendo '%s' para '%s'...", filename, agencia_str)

            if isinstance(file_path_or_buffer, str):
                with open(file_path_or_buffer, "rb") as f:
                    message = await bot.send_document(
                        chat_id=self.storage_channel_id,
                        document=f,
                        filename=filename,
                        caption=caption,
                    )
            else:
                message = await bot.send_document(
                    chat_id=self.storage_channel_id,
                    document=file_path_or_buffer,
                    filename=filename,
                    caption=caption,
                )

            file_id = message.document.file_id
            logger.info("[TelegramStorage] Archivo subido. File ID: %s", file_id)
            return file_id

        except Exception as e:
            logger.error("[TelegramStorage] Error subiendo archivo: %s", e)
            return None

    def upload_file_sync(
        self, file_path_or_buffer, filename: str = "documento.pdf", caption: str = None
    ):
        """Version sincrona de upload_file. Segura para usar en vistas Django."""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(
                self.upload_file(file_path_or_buffer, filename, caption)
            )
            loop.close()
            return result
        except Exception as e:
            logger.error("[TelegramStorage] Error en upload sincrono: %s", e)
            return None

    async def get_file_url(self, file_id: str):
        """Obtiene una URL temporal de descarga para un file_id (~1h de validez)."""
        if not self.bot_token:
            return None

        try:
            from telegram import Bot  # noqa: PLC0415

            bot = Bot(token=self.bot_token)
            file_obj = await bot.get_file(file_id)
            return file_obj.file_path
        except Exception as e:
            logger.error("[TelegramStorage] Error recuperando URL de '%s': %s", file_id, e)
            return None


# ============================================================================
# SECTION 4: LOGO/IMAGE UPLOAD UTILITIES
# ============================================================================


def upload_logo_to_telegram(file_obj, filename: str = "logo.png", agencia=None):
    """
    Sube una imagen/logo a Telegram (Storage Channel) y devuelve el file_id.

    Args:
        file_obj: Objeto tipo file (con .read()) o bytes.
        filename: Nombre del archivo.
        agencia: Instancia de Agencia (requerido para aislamiento multitenant).

    Returns:
        str: file_id de Telegram, o None si falla.
    """
    cfg = _resolve_telegram_config(agencia, purpose="storage")
    token = cfg["token"]
    channel_id = cfg["chat_id"]

    if not token or not channel_id:
        agencia_str = getattr(agencia, "nombre", "sistema") if agencia else "sistema"
        logger.error(
            "[TelegramStorage] Config incompleta para '%s'. Token=%s, Channel=%s",
            agencia_str,
            bool(token),
            channel_id,
        )
        return None

    url = f"https://api.telegram.org/bot{token}/sendPhoto"

    try:
        if hasattr(file_obj, "read"):
            file_obj.seek(0)
            files = {"photo": (filename, file_obj.read())}
        else:
            files = {"photo": (filename, file_obj)}

        data = {"chat_id": channel_id, "caption": f"Storage: {filename}"}
        response = requests.post(url, data=data, files=files, timeout=30)
        result = response.json()

        if result.get("ok"):
            photo_data = result["result"]["photo"][-1]
            file_id = photo_data["file_id"]
            logger.info("[TelegramStorage] Logo subido. FileID: %s", file_id)
            return file_id
        else:
            logger.error("[TelegramStorage] Error subiendo logo: %s", result.get("description"))
            return None

    except Exception as e:
        logger.error("[TelegramStorage] Fallo critico subiendo logo: %s", e)
        return None


def get_telegram_file_url(file_id: str, agencia=None):
    """
    Genera la URL para que el frontend pueda mostrar una imagen almacenada en Telegram.
    Retorna None si no hay token configurado para la agencia.
    """
    cfg = _resolve_telegram_config(agencia, purpose="notify")
    token = cfg["token"]
    if not token or not file_id:
        return None
    return f"https://api.telegram.org/bot{token}/getFile?file_id={file_id}"


# ============================================================================
# SECTION 5: CLIENT-FACING TELEGRAM NOTIFICATIONS
# ============================================================================


def send_telegram_to_client(
    cliente,
    message: str,
    parse_mode: str = "HTML",
    document_url: str = None,
    caption: str = None,
) -> bool:
    """Envia un mensaje de Telegram a un cliente.

    Usa el telegram_chat_id almacenado en el modelo Cliente.
    Si el cliente no tiene chat_id registrado, falla silenciosamente.

    Args:
        cliente: Instancia de Cliente
        message: Texto del mensaje
        parse_mode: HTML o Markdown
        document_url: URL opcional de documento a adjuntar
        caption: Titulo del documento adjunto
    """
    if not cliente or not getattr(cliente, "telegram_chat_id", None):
        return False

    # Obtener la agencia del cliente para usar su bot
    agencia = getattr(cliente, "agencia", None)

    if document_url:
        return TelegramNotificationService.send_document(
            file_path=document_url,
            caption=caption or message,
            chat_id=cliente.telegram_chat_id,
            agencia=agencia,
        )
    else:
        return TelegramNotificationService.send_message(
            message=message,
            chat_id=cliente.telegram_chat_id,
            parse_mode=parse_mode,
            agencia=agencia,
        )


def notify_cliente_confirmacion_venta(cliente, venta) -> bool:
    """Envia confirmacion de venta al cliente por Telegram."""
    msg = (
        f"\u2705 <b>Reserva Confirmada</b>\n\n"
        f"Hola <b>{cliente.nombres}</b>, tu reserva ha sido confirmada.\n\n"
        f"\U0001f4cb <b>Reserva:</b> #{venta.id}\n"
        f"\U0001f4b0 <b>Total:</b> ${venta.total:.2f}\n"
        f"\U0001f4c5 <b>Fecha:</b> {venta.fecha_creacion.strftime('%d/%m/%Y')}\n\n"
        f"Gracias por confiar en nosotros. \U0001f389"
    )
    return send_telegram_to_client(cliente, msg)


def notify_cliente_recordatorio_pago(cliente, venta) -> bool:
    """Envia recordatorio de pago al cliente por Telegram."""
    msg = (
        f"\u23f0 <b>Recordatorio de Pago</b>\n\n"
        f"Hola <b>{cliente.nombres}</b>, tienes un pago pendiente.\n\n"
        f"\U0001f4cb <b>Reserva:</b> #{venta.id}\n"
        f"\U0001f4b0 <b>Monto pendiente:</b> ${venta.saldo_pendiente:.2f}\n\n"
        f"Por favor realiza el pago a la brevedad para confirmar tu reserva."
    )
    return send_telegram_to_client(cliente, msg)


def notify_cliente_alerta_vuelo(cliente, venta, cambio: str) -> bool:
    """Envia alerta de cambio de vuelo al cliente por Telegram."""
    msg = (
        f"\u2708\ufe0f <b>Actualizacion de Vuelo</b>\n\n"
        f"Hola <b>{cliente.nombres}</b>, hay un cambio en tu itinerario.\n\n"
        f"{cambio}\n\n"
        f"\U0001f4cb <b>Reserva:</b> #{venta.id}\n\n"
        f"Comunicarte con tu agente para mas detalles."
    )
    return send_telegram_to_client(cliente, msg)


def notify_cliente_alerta_migratoria(cliente, destino: str, requisitos: str) -> bool:
    """Envia alerta migratoria al cliente por Telegram."""
    msg = (
        f"\U0001f6c2 <b>Requisitos Migratorios</b>\n\n"
        f"Hola <b>{cliente.nombres}</b>, para tu viaje a <b>{destino}</b> necesitas:\n\n"
        f"{requisitos}\n\n"
        f"Verifica que toda tu documentacion este en orden antes del vuelo."
    )
    return send_telegram_to_client(cliente, msg)


def notify_cliente_cotizacion(cliente, cotizacion_data: dict) -> bool:
    """Envia una cotizacion al cliente por Telegram."""
    msg = (
        f"\U0001f4c4 <b>Tu Cotizacion</b>\n\n"
        f"Hola <b>{cliente.nombres}</b>, tenemos una cotizacion para ti:\n\n"
        f"\u2708\ufe0f <b>Destino:</b> {cotizacion_data.get('destino', '')}\n"
        f"\U0001f4c5 <b>Fechas:</b> {cotizacion_data.get('fechas', '')}\n"
        f"\U0001f4b0 <b>Total estimado:</b> ${cotizacion_data.get('total', 0):.2f}\n\n"
        f"Responde este mensaje o contacta a tu agente para confirmar."
    )
    return send_telegram_to_client(cliente, msg)

"""
Telegram Unified Service
Consolidated service for all Telegram operations:
- Message sending (Text/HTML/Markdown)
- Document/File sending (Local path, URL, File ID)
- File retrieval (get_file_url)
- Async/Sync wrappers for alerts and files
- Storage service (Channel as unlimited storage)
- Logo/Image upload utilities
"""

import asyncio
import logging
import os

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

# ============================================================================
# SECTION 1: CORE MESSAGING (HTTP API)
# ============================================================================


class TelegramNotificationService:
    """
    Servicio unificado para enviar notificaciones y archivos a Telegram.
    Centraliza la lógica de envío para Boletos, Facturas y otros documentos.
    """

    @staticmethod
    def send_message(
        message: str, chat_id: str = None, parse_mode: str = "HTML", agencia=None, **kwargs
    ) -> bool:
        """Envía un mensaje de texto simple."""
        try:
            token = settings.TELEGRAM_BOT_TOKEN
            if agencia and hasattr(agencia, "configuracion_api") and agencia.configuracion_api:
                token = agencia.configuracion_api.get("TELEGRAM_BOT_TOKEN", token)

            chat = chat_id
            if not chat:
                if agencia and hasattr(agencia, "configuracion_api"):
                    chat = agencia.configuracion_api.get(
                        "TELEGRAM_CHANNEL_ID"
                    ) or agencia.configuracion_api.get("TELEGRAM_GROUP_ID")

                if not chat:
                    chat = getattr(settings, "TELEGRAM_GROUP_ID", None) or getattr(
                        settings, "TELEGRAM_CHANNEL_ID", None
                    )

            if not token or not chat:
                logger.warning(
                    f"Telegram Config Missing: Token={bool(token)}, Chat={chat} (Agencia: {agencia})"
                )
                return False

            url = f"https://api.telegram.org/bot{token}/sendMessage"
            payload = {"chat_id": chat, "text": message, "parse_mode": parse_mode}
            if kwargs:
                payload.update(kwargs)
            response = requests.post(url, data=payload, timeout=30)
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Error sending Telegram message: {e}")
            return False

    @staticmethod
    def send_document(file_path: str, caption: str = None, chat_id: str = None, agencia=None):
        """Envía un documento (PDF, etc.) a Telegram via Path Local, URL, o File ID."""
        try:
            token = settings.TELEGRAM_BOT_TOKEN
            if agencia and hasattr(agencia, "configuracion_api") and agencia.configuracion_api:
                token = agencia.configuracion_api.get("TELEGRAM_BOT_TOKEN", token)

            chat = chat_id
            if not chat:
                if agencia and hasattr(agencia, "configuracion_api"):
                    chat = (
                        agencia.configuracion_api.get("TELEGRAM_STORAGE_CHANNEL_ID")
                        or agencia.configuracion_api.get("TELEGRAM_CHANNEL_ID")
                        or agencia.configuracion_api.get("TELEGRAM_GROUP_ID")
                    )

                if not chat:
                    chat = getattr(settings, "TELEGRAM_STORAGE_CHANNEL_ID", None) or getattr(
                        settings, "TELEGRAM_GROUP_ID", None
                    )

            if not token or not chat:
                logger.warning(f"Telegram Config Missing: Token={bool(token)}, Chat={chat}")
                return False

            url_api = f"https://api.telegram.org/bot{token}/sendDocument"

            if file_path.startswith("http"):
                logger.info(f"Enviando documento vía URL: {file_path}")
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
                logger.info(f"Enviando documento vía File ID: {file_path}")
                data = {
                    "chat_id": chat,
                    "document": file_path,
                    "caption": caption,
                    "parse_mode": "HTML",
                }
                response = requests.post(url_api, data=data, timeout=60)

            if response.status_code != 200:
                logger.error(f"Telegram API Error: {response.text}")
                response.raise_for_status()

            try:
                resp_json = response.json()
                if resp_json.get("ok"):
                    document = resp_json["result"].get("document")
                    file_id = document.get("file_id") if document else None
                    if file_id:
                        logger.info(f"✅ Documento enviado. File ID: {file_id}")
                        return file_id
            except Exception as e_json:
                logger.warning(f"No se pudo extraer file_id de Telegram: {e_json}")

            return True

        except Exception as e:
            logger.error(f"Error sending Telegram document: {e}")
            return False

    @staticmethod
    def get_file_url(file_id: str, agencia=None):
        """
        Obtiene la URL temporal de descarga de un archivo de Telegram.
        """
        try:
            token = settings.TELEGRAM_BOT_TOKEN
            if agencia and hasattr(agencia, "configuracion_api") and agencia.configuracion_api:
                token = agencia.configuracion_api.get("TELEGRAM_BOT_TOKEN", token)

            if not token:
                return None

            url_api = f"https://api.telegram.org/bot{token}/getFile"
            response = requests.post(url_api, data={"file_id": file_id}, timeout=30)

            if response.status_code == 200:
                result = response.json().get("result", {})
                file_path = result.get("file_path")

                if file_path:
                    return f"https://api.telegram.org/file/bot{token}/{file_path}"

            logger.error(f"Error getting file info from Telegram: {response.text}")
            return None

        except Exception as e:
            logger.error(f"Error resolving Telegram file URL: {e}")
            return None


def enviar_alerta_telegram(mensaje: str, chat_id: str = None, agencia=None) -> bool:
    """
    Función shim para enviar alertas rápidas a Telegram.
    """
    success = TelegramNotificationService.send_message(mensaje, chat_id=chat_id, agencia=agencia)
    if success:
        logger.info("Telegram alert sent successfully.")
    else:
        logger.error("Failed to send Telegram alert.")
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
        Envía una alerta al Grupo Configurado (o al Admin si no hay grupo).
        """
        token = token or os.getenv("TELEGRAM_BOT_TOKEN")
        if not target_chat_id:
            admin_id = os.getenv("TELEGRAM_ADMIN_ID")
            group_id = os.getenv("TELEGRAM_GROUP_ID")
            target_chat_id = group_id if group_id else admin_id

        if not token or not target_chat_id:
            logger.warning("Telegram Config incompleto (Falta Token o Target ID).")
            return False

        try:
            bot = Bot(token=token)
            await bot.send_message(chat_id=target_chat_id, text=message, parse_mode="HTML")
            return True
        except Exception as e:
            logger.error(f"Error enviando alerta Telegram: {e}")
            return False

    def send_telegram_alert_sync(message: str, token: str = None, target_chat_id: str = None):
        """Wrapper síncrono para usar en contextos donde no se puede usar async/await"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(send_telegram_alert(message, token, target_chat_id))
            loop.close()
        except Exception as e:
            logger.error(f"Error en wrapper síncrono de Telegram: {e}")

    async def send_telegram_file(
        file_path: str, caption: str = None, token: str = None, target_chat_id: str = None
    ) -> bool:
        """Envía un archivo (PDF, imagen, etc.) al Grupo o Admin."""
        token = token or os.getenv("TELEGRAM_BOT_TOKEN")
        if not target_chat_id:
            admin_id = os.getenv("TELEGRAM_ADMIN_ID")
            group_id = os.getenv("TELEGRAM_GROUP_ID")
            target_chat_id = group_id if group_id else admin_id

        if not token or not target_chat_id:
            return False

        try:
            if not os.path.exists(file_path):
                logger.error(f"Archivo no encontrado para enviar a Telegram: {file_path}")
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
            logger.error(f"Error enviando archivo Telegram: {e}")
            return False

    def send_telegram_file_sync(
        file_path: str, caption: str = None, token: str = None, target_chat_id: str = None
    ):
        """Wrapper síncrono para enviar archivos."""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(send_telegram_file(file_path, caption, token, target_chat_id))
            loop.close()
        except Exception as e:
            logger.error(f"Error en wrapper síncrono de Telegram (File): {e}")

except ImportError:
    logger.warning("python-telegram-bot no está instalado. Async wrappers deshabilitados.")

    async def send_telegram_alert(
        message: str, token: str = None, target_chat_id: str = None
    ) -> bool:
        logger.error("Telegram async wrappers no disponibles: falta python-telegram-bot")
        return False

    def send_telegram_alert_sync(message: str, token: str = None, target_chat_id: str = None):
        logger.error("Telegram async wrappers no disponibles: falta python-telegram-bot")

    async def send_telegram_file(
        file_path: str, caption: str = None, token: str = None, target_chat_id: str = None
    ) -> bool:
        logger.error("Telegram async wrappers no disponibles: falta python-telegram-bot")
        return False

    def send_telegram_file_sync(
        file_path: str, caption: str = None, token: str = None, target_chat_id: str = None
    ):
        logger.error("Telegram async wrappers no disponibles: falta python-telegram-bot")


# ============================================================================
# SECTION 3: STORAGE SERVICE (Channel as Unlimited Storage)
# ============================================================================


class TelegramStorageService:
    """
    Servicio para usar un Canal de Telegram como almacenamiento ilimitado.
    Sube archivos recuperando su file_id y permite generar links temporales.
    """

    def __init__(self):
        self.bot_token = getattr(settings, "TELEGRAM_BOT_TOKEN", None)
        self.storage_channel_id = os.environ.get("TELEGRAM_STORAGE_CHANNEL_ID", None)

        if not self.bot_token:
            logger.warning(
                "TELEGRAM_BOT_TOKEN no configurado. TelegramStorageService deshabilitado."
            )

    async def upload_file(
        self, file_path_or_buffer, filename: str = "documento.pdf", caption: str = None
    ):
        """Sube un archivo a Telegram y retorna su file_id."""
        if not self.bot_token or not self.storage_channel_id:
            logger.error("Falta configuración de Telegram (Token o Channel ID)")
            return None

        try:
            from telegram import Bot

            bot = Bot(token=self.bot_token)

            logger.info(f"Subiendo {filename} a Telegram Storage ({self.storage_channel_id})...")

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
            logger.info(f"✅ Archivo subido exitosamente. File ID: {file_id}")
            return file_id

        except Exception as e:
            logger.error(f"Error subiendo archivo a Telegram: {e}")
            return None

    async def get_file_url(self, file_id: str):
        """Obtiene una URL temporal de descarga para un file_id."""
        if not self.bot_token:
            return None

        try:
            from telegram import Bot

            bot = Bot(token=self.bot_token)
            file_obj = await bot.get_file(file_id)
            return file_obj.file_path
        except Exception as e:
            logger.error(f"Error recuperando URL de archivo Telegram {file_id}: {e}")
            return None


# ============================================================================
# SECTION 4: LOGO/IMAGE UPLOAD UTILITIES
# ============================================================================


def upload_logo_to_telegram(file_obj, filename: str = "logo.png"):
    """
    Sube un archivo a Telegram (Storage Channel) y devuelve el file_id.
    """
    token = getattr(settings, "TELEGRAM_BOT_TOKEN", os.getenv("TELEGRAM_BOT_TOKEN"))
    channel_id = getattr(settings, "TELEGRAM_STORAGE_CHANNEL_ID", "-1003225870613")

    if not token or not channel_id:
        logger.error("Configuración de Telegram Storage incompleta.")
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
            logger.info(f"✅ Logo subido a Telegram Storage. FileID: {file_id}")
            return file_id
        else:
            logger.error(f"❌ Error subiendo a Telegram: {result.get('description')}")
            return None

    except Exception as e:
        logger.error(f"💥 Fallo crítico en telegram_storage: {e}")
        return None


def get_telegram_file_url(file_id: str):
    """
    Genera una URL para que el frontend pueda mostrar la imagen.
    """
    token = getattr(settings, "TELEGRAM_BOT_TOKEN", os.getenv("TELEGRAM_BOT_TOKEN"))
    if not token or not file_id:
        return None

    return f"https://api.telegram.org/bot{token}/getFile?file_id={file_id}"


# ============================================================================
# SECTION 5: CLIENT-FACING TELEGRAM NOTIFICATIONS
# ============================================================================


def send_telegram_to_client(
    cliente, message: str, parse_mode: str = "HTML", document_url: str = None, caption: str = None
) -> bool:
    """Envía un mensaje de Telegram a un cliente.

    Usa el telegram_chat_id almacenado en el modelo Cliente.
    Si el cliente no tiene chat_id registrado, falla silenciosamente.

    Args:
        cliente: Instancia de Cliente
        message: Texto del mensaje
        parse_mode: HTML o Markdown
        document_url: URL opcional de documento a adjuntar
        caption: Título del documento adjunto
    """
    if not cliente or not cliente.telegram_chat_id:
        return False

    if document_url:
        return TelegramNotificationService.send_document(
            file_path=document_url,
            caption=caption or message,
            chat_id=cliente.telegram_chat_id,
        )
    else:
        return TelegramNotificationService.send_message(
            message=message,
            chat_id=cliente.telegram_chat_id,
            parse_mode=parse_mode,
        )


def notify_cliente_confirmacion_venta(cliente, venta) -> bool:
    """Envía confirmación de venta al cliente por Telegram."""
    msg = (
        f"✅ <b>Reserva Confirmada</b>\n\n"
        f"Hola <b>{cliente.nombres}</b>, tu reserva ha sido confirmada.\n\n"
        f"📋 <b>Reserva:</b> #{venta.id}\n"
        f"💰 <b>Total:</b> ${venta.total:.2f}\n"
        f"📅 <b>Fecha:</b> {venta.fecha_creacion.strftime('%d/%m/%Y')}\n\n"
        f"Gracias por confiar en nosotros. 🎉"
    )
    return send_telegram_to_client(cliente, msg)


def notify_cliente_recordatorio_pago(cliente, venta) -> bool:
    """Envía recordatorio de pago al cliente por Telegram."""
    msg = (
        f"⏰ <b>Recordatorio de Pago</b>\n\n"
        f"Hola <b>{cliente.nombres}</b>, tienes un pago pendiente.\n\n"
        f"📋 <b>Reserva:</b> #{venta.id}\n"
        f"💰 <b>Monto pendiente:</b> ${venta.saldo_pendiente:.2f}\n\n"
        f"Por favor realiza el pago a la brevedad para confirmar tu reserva."
    )
    return send_telegram_to_client(cliente, msg)


def notify_cliente_alerta_vuelo(cliente, venta, cambio: str) -> bool:
    """Envía alerta de cambio de vuelo al cliente por Telegram."""
    msg = (
        f"✈️ <b>Actualización de Vuelo</b>\n\n"
        f"Hola <b>{cliente.nombres}</b>, hay un cambio en tu itinerario.\n\n"
        f"{cambio}\n\n"
        f"📋 <b>Reserva:</b> #{venta.id}\n\n"
        f"Comunícate con tu agente para más detalles."
    )
    return send_telegram_to_client(cliente, msg)


def notify_cliente_alerta_migratoria(cliente, destino: str, requisitos: str) -> bool:
    """Envía alerta migratoria al cliente por Telegram."""
    msg = (
        f"🛂 <b>Requisitos Migratorios</b>\n\n"
        f"Hola <b>{cliente.nombres}</b>, para tu viaje a <b>{destino}</b> necesitas:\n\n"
        f"{requisitos}\n\n"
        f"Verifica que toda tu documentación esté en orden antes del vuelo."
    )
    return send_telegram_to_client(cliente, msg)


def notify_cliente_cotizacion(cliente, cotizacion_data: dict) -> bool:
    """Envía una cotización al cliente por Telegram."""
    msg = (
        f"📄 <b>Tu Cotización</b>\n\n"
        f"Hola <b>{cliente.nombres}</b>, tenemos una cotización para ti:\n\n"
        f"✈️ <b>Destino:</b> {cotizacion_data.get('destino', '')}\n"
        f"📅 <b>Fechas:</b> {cotizacion_data.get('fechas', '')}\n"
        f"💰 <b>Total estimado:</b> ${cotizacion_data.get('total', 0):.2f}\n\n"
        f"Responde este mensaje o contacta a tu agente para confirmar."
    )
    return send_telegram_to_client(cliente, msg)

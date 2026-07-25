"""Servicio de notification dispatcher para la aplicación communications.
"""

import logging
import os

from django.conf import settings
from django.core.mail import EmailMessage

logger = logging.getLogger(__name__)


def enviar_notificacion_telegram(
    agencia, sistema, localizador, numero_boleto, pasajero, aerolinea, pdf_path
):
    # enviar_notificacion_telegram: Envía ar notificacion telegram. Args: datos del mensaje. Returns: resultado del envío.
    from apps.communications.services.telegram_unified import send_telegram_file_sync

    mensaje = (
        f"✈️ <b>Boleto {sistema} Procesado</b>\n\n"
        f"📍 PNR: <code>{localizador or 'N/A'}</code>\n"
        f"🎫 Boleto: {numero_boleto}\n"
        f"👤 Pasajero: {pasajero or 'N/A'}\n"
        f"✈️ Aerolínea: {aerolinea or 'N/A'}\n\n"
        f"<i>TravelHub - Oficina Digital</i>"
    )

    logger.info("📤 Enviando Telegram a Admin...")
    return send_telegram_file_sync(
        pdf_path,
        caption=mensaje,
        token=agencia.telegram_bot_token,
        target_chat_id=agencia.telegram_chat_id,
    )


def enviar_notificacion_whatsapp(
    destination, sistema, localizador, numero_boleto, pasajero, aerolinea, pdf_filename
):
    # enviar_notificacion_whatsapp: Envía ar notificacion whatsapp. Args: datos del mensaje. Returns: resultado del envío.
    from apps.communications.services.whatsapp_unified import enviar_whatsapp

    mensaje = f"""✈️ *Boleto {sistema} Procesado*

📍 PNR: *{localizador or "N/A"}*
🎫 Boleto: {numero_boleto}
👤 Pasajero: {pasajero or "N/A"}
✈️ Aerolínea: {aerolinea or "N/A"}
📄 PDF: {pdf_filename}

_TravelHub - Sistema Automático_"""

    return enviar_whatsapp(destination, mensaje)


def enviar_notificacion_email(
    agencia, destination, sistema, localizador, numero_boleto, pasajero, aerolinea, pdf_path
):
    # enviar_notificacion_email: Envía ar notificacion email. Args: datos del mensaje. Returns: resultado del envío.
    try:
        email_msg = EmailMessage(
            subject=f"Boleto {sistema} Procesado - {localizador}",
            body=f"""Boleto procesado automáticamente:

Sistema: {sistema}
PNR: {localizador}
Boleto: {numero_boleto}
Pasajero: {pasajero}
Aerolínea: {aerolinea}

PDF adjunto.

TravelHub - Sistema Automático""",
            to=[destination],
        )

        if agencia.email_principal:
            email_msg.from_email = agencia.email_principal

        email_msg.attach_file(pdf_path)
        email_msg.send()

        logger.info(f"✅ Email enviado: {numero_boleto}")
        return True
    except Exception as e:
        logger.error(f"❌ Error enviando email: {e}")
        return False


def enviar_respaldo_email(agencia, boleto, pdf_path):
    # enviar_respaldo_email: Envía ar respaldo email. Args: datos del mensaje. Returns: resultado del envío.
    try:
        destino = getattr(agencia, "email_soporte", None)
        if not destino:
            return

        email_msg = EmailMessage(
            subject=f"Boleto Auto (Respaldo) - {boleto.localizador_pnr}",
            body=f"Respaldo automático ID {boleto.pk} para {agencia.nombre}",
            from_email=agencia.email_principal or settings.EMAIL_HOST_USER,
            to=[destino],
        )
        if pdf_path and os.path.exists(pdf_path):
            email_msg.attach_file(pdf_path)
        email_msg.send()
    except Exception as e:
        logger.warning(f"Error enviando respaldo email: {e}")

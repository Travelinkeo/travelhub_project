"""
Notification Dispatcher (Unified)
Consolidated service for all notification operations:
- Multi-channel routing (Email, WhatsApp, Telegram)
- AI-generated notifications (flight changes)
- Ticket notifications (processed, flight reminders)
- Payment confirmations (Email + WhatsApp orchestration)
- Migration alerts
- Welcome emails
- PDF report attachments
"""

import logging
from abc import ABC, abstractmethod
from typing import Any

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags

from apps.communications.services.email_unified import enviar_email_generico
from apps.communications.services.whatsapp_unified import (
    enviar_whatsapp_confirmacion_pago,
    enviar_whatsapp_confirmacion_venta,
    enviar_whatsapp_recordatorio_pago,
)

logger = logging.getLogger(__name__)

# ============================================================================
# SECTION 1: CHANNEL ABSTRACTION
# ============================================================================


class NotificationChannel(ABC):
    """Interfaz base para canales de notificación"""

    @abstractmethod
    def send(self, recipient: str, message: str, **kwargs) -> bool:
        """Envía notificación por este canal"""
        pass

    @abstractmethod
    def is_available(self, agencia=None) -> bool:
        """Verifica si el canal está disponible"""
        pass


class EmailChannel(NotificationChannel):
    """Canal de notificación por email"""

    def send(self, recipient: str, message: str, **kwargs) -> bool:
        """send."""
        try:
            from apps.common.tasks import send_email_task

            subject = kwargs.get("subject", "Notificación TravelHub")
            agencia_id = None
            agencia = kwargs.get("agencia")
            if agencia and hasattr(agencia, "pk"):
                agencia_id = agencia.pk
            send_email_task.delay(
                recipient=recipient,
                subject=subject,
                message=message,
                agencia_id=agencia_id,
            )
            return True
        except Exception as e:
            logger.error(f"Error encolando email: {e}")
            return False

    def is_available(self, agencia=None) -> bool:
        """is_available."""
        if agencia:
            email_config = agencia.configuracion_correo
            if email_config and email_config.get("EMAIL_HOST"):
                return True
        return bool(settings.EMAIL_HOST_USER)


class WhatsAppChannel(NotificationChannel):
    """Canal de notificación por WhatsApp"""

    def send(self, recipient: str, message: str, **kwargs) -> bool:
        """send."""
        try:
            from apps.common.tasks import send_whatsapp_task

            agencia_id = None
            agencia = kwargs.get("agencia")
            if agencia and hasattr(agencia, "pk"):
                agencia_id = agencia.pk
            send_whatsapp_task.delay(
                sender_id=recipient,
                recipient_number=recipient,
                message_text=message,
                agencia_id=agencia_id,
            )
            return True
        except Exception as e:
            logger.error(f"Error encolando WhatsApp: {e}")
            return False

    def is_available(self, agencia=None) -> bool:
        """is_available."""
        if agencia:
            if getattr(agencia, "subdominio_slug", None):
                return True
        return getattr(settings, "WHATSAPP_NOTIFICATIONS_ENABLED", False)


class TelegramChannel(NotificationChannel):
    """Canal de notificación por Telegram"""

    def send(self, recipient: str, message: str, **kwargs) -> bool:
        """send."""
        try:
            from apps.common.tasks import send_telegram_task

            agencia_id = None
            agencia = kwargs.get("agencia")
            if agencia and hasattr(agencia, "pk"):
                agencia_id = agencia.pk
            send_telegram_task.delay(message=message, chat_id=recipient, agencia_id=agencia_id)
            return True
        except Exception as e:
            logger.error(f"Error encolando Telegram: {e}")
            return False

    def is_available(self, agencia=None) -> bool:
        """is_available."""
        if agencia:
            token = getattr(agencia, "telegram_bot_token", None)
            chat = getattr(agencia, "telegram_chat_id", None)
            if token and chat:
                return True
        return bool(getattr(settings, "TELEGRAM_BOT_TOKEN", None)) and (
            bool(getattr(settings, "TELEGRAM_GROUP_ID", None))
            or bool(getattr(settings, "TELEGRAM_CHANNEL_ID", None))
        )


class NotificationDispatcher:
    """Servicio centralizado para envío de notificaciones multi-canal"""

    def __init__(self):
        """__init__."""
        self.channels = {
            "email": EmailChannel(),
            "whatsapp": WhatsAppChannel(),
            "telegram": TelegramChannel(),
        }

    def notify(self, event: str, recipient: dict, data: dict) -> dict[str, bool]:
        """
        Envía notificación por todos los canales disponibles

        Args:
            event: Tipo de evento (confirmacion_venta, cambio_estado, etc.)
            recipient: Dict con email, telefono y telegram_chat_id del destinatario
            data: Datos para construir el mensaje

        Returns:
            Dict con resultado por canal
        """
        results = {}
        agencia = data.get("agencia")
        if not agencia and "venta" in data and data["venta"]:
            agencia = getattr(data["venta"], "agencia", None)
        elif not agencia and "pago" in data and data["pago"]:
            agencia = getattr(data["pago"].venta, "agencia", None)
        elif not agencia and "boleto" in data and data["boleto"]:
            boleto = data["boleto"]
            if getattr(boleto, "venta_asociada", None):
                agencia = getattr(boleto.venta_asociada, "agencia", None)
            else:
                agencia = getattr(boleto, "agencia", None)

        for channel_name, channel in self.channels.items():
            if not channel.is_available(agencia=agencia):
                logger.debug(f"Canal {channel_name} no disponible")
                continue

            recipient_id = self._get_recipient_for_channel(recipient, channel_name, agencia=agencia)
            if not recipient_id:
                logger.debug(f"No hay destinatario para canal {channel_name}")
                continue

            message = self._build_message(event, data, channel_name)
            kwargs = {**data, "agencia": agencia}
            results[channel_name] = channel.send(recipient_id, message, **kwargs)

        return results

    def _get_recipient_for_channel(self, recipient: dict, channel: str, agencia=None) -> str:
        """Obtiene el destinatario apropiado para el canal"""
        if channel == "email":
            return recipient.get("email")
        elif channel == "whatsapp":
            return recipient.get("telefono")
        elif channel == "telegram":
            chat_id = recipient.get("telegram_chat_id")
            if not chat_id and agencia:
                chat_id = getattr(agencia, "telegram_chat_id", None)
            return chat_id
        return None

    def _build_message(self, event: str, data: dict, channel: str) -> str:
        """Construye el mensaje según el evento y canal"""
        if event == "confirmacion_venta":
            return self._build_venta_message(data, channel)
        elif event == "cambio_estado":
            return self._build_estado_message(data, channel)
        elif event == "recordatorio_pago":
            return self._build_pago_message(data, channel)
        return str(data)

    def _build_venta_message(self, data: dict, channel: str) -> str:
        """_build_venta_message."""
        venta = data.get("venta")
        if channel == "whatsapp":
            return (
                f"✅ Venta confirmada\nLocalizador: {venta.localizador}\nTotal: {venta.total_venta}"
            )
        return f"Su venta {venta.localizador} ha sido confirmada."

    def _build_estado_message(self, data: dict, channel: str) -> str:
        """_build_estado_message."""
        venta = data.get("venta")
        estado = data.get("estado_nuevo")
        return f"Estado de venta {venta.localizador} cambió a: {estado}"

    def _build_pago_message(self, data: dict, channel: str) -> str:
        """_build_pago_message."""
        venta = data.get("venta")
        return f"Recordatorio: Pago pendiente para venta {venta.localizador}"


notification_dispatcher = NotificationDispatcher()


# ============================================================================
# SECTION 2: PAYMENT & SALE ORCHESTRATION
# ============================================================================


def notificar_confirmacion_pago(pago_venta):
    """
    Orquestador de notificaciones para pagos recibidos.
    Envía email y WhatsApp (si están configurados).
    """
    from apps.communications.services.email_unified import enviar_confirmacion_pago

    try:
        enviar_confirmacion_pago(pago_venta)
    except Exception as e:
        logger.error(f"Error en notificación de pago (Email): {e}")

    try:
        enviar_whatsapp_confirmacion_pago(pago_venta)
    except Exception as e:
        logger.error(f"Error en notificación de pago (WhatsApp): {e}")


def notificar_recordatorio_pago(venta) -> dict[str, bool]:
    """
    Orquestador de recordatorios de pago.
    Envía email y WhatsApp. Retorna dict con resultados por canal.
    """
    from apps.communications.services.email_unified import enviar_recordatorio_pago

    resultados = {"email": False, "whatsapp": False}

    try:
        resultados["email"] = enviar_recordatorio_pago(venta)
    except Exception as e:
        logger.error(f"Error en recordatorio de pago (Email): {e}")

    try:
        resultados["whatsapp"] = enviar_whatsapp_recordatorio_pago(venta)
    except Exception as e:
        logger.error(f"Error en recordatorio de pago (WhatsApp): {e}")

    return resultados


def notificar_confirmacion_venta(venta):
    """
    Orquestador de confirmación de venta.
    Envía email y WhatsApp.
    """
    from apps.communications.services.email_unified import enviar_confirmacion_venta

    try:
        enviar_confirmacion_venta(venta)
    except Exception as e:
        logger.error(f"Error en confirmación de venta (Email): {e}")

    try:
        enviar_whatsapp_confirmacion_venta(venta)
    except Exception as e:
        logger.error(f"Error en confirmación de venta (WhatsApp): {e}")


# ============================================================================
# SECTION 3: AI-GENERATED NOTIFICATIONS (Flight Changes)
# ============================================================================


def generate_whatsapp_notification(cliente, datos_cambio: dict[str, Any]) -> str:
    """
    Usa Gemini para redactar un mensaje de WhatsApp claro y tranquilizador
    sobre cambios urgentes en itinerario de vuelo.
    """
    logging.info(f"Generando mensaje de WhatsApp para {cliente.get_nombre_completo()}")

    pnr = datos_cambio.get("pnr", "N/A")
    aerolinea = datos_cambio.get("aerolinea", "N/A")
    vuelo_antiguo = datos_cambio.get("vuelo_antiguo", {})
    vuelo_nuevo = datos_cambio.get("vuelo_nuevo", {})

    prompt = f"""
    Actúa como un asistente de viajes proactivo y empático de la agencia TravelHub.
    Tu tarea es redactar un mensaje de WhatsApp para notificar a un cliente sobre un cambio urgente en su itinerario de vuelo.
    El tono debe ser tranquilizador, claro y profesional.

    **Contexto:**
    - **Nombre del Cliente:** {cliente.get_nombre_completo()}
    - **Código de Reserva (PNR):** {pnr}
    - **Aerolínea:** {aerolinea}

    **Detalles del Cambio:**
    - **Vuelo Original:**
        - Fecha: {vuelo_antiguo.get("fecha", "N/A")}
        - Hora de Salida: {vuelo_antiguo.get("hora_salida", "N/A")}
    - **NUEVO Vuelo:**
        - Fecha: {vuelo_nuevo.get("fecha", "N/A")}
        - Hora de Salida: {vuelo_nuevo.get("hora_salida", "N/A")}

    **Instrucciones para el Mensaje:**
    1. Saluda al cliente por su nombre.
    2. Identifícate como un asistente de TravelHub.
    3. Informa sobre el cambio de horario en su vuelo, mencionando el PNR.
    4. Presenta claramente la información del vuelo original y del nuevo vuelo.
    5. Asegúrale al cliente que su reserva está confirmada.
    6. Menciona que su calendario ha sido actualizado automáticamente.
    7. Ofrécele ayuda para cualquier duda.

    Genera únicamente el texto del mensaje de WhatsApp.
    """
    from django.utils.module_loading import import_string

    generate_content = import_string("apps.automation.services.ai_engine.generate_content")
    return generate_content(prompt)


def handle_urgent_notification(extracted_data: dict[str, Any]):
    """
    Orquesta el proceso de manejo de una notificación urgente.
    - Busca la venta por PNR
    - Actualiza Google Calendar si existe
    - Genera mensaje IA y envía por WhatsApp
    """
    pnr = extracted_data.get("pnr") or extracted_data.get("codigo_reserva")
    if not pnr:
        logging.error("No se encontró PNR o código de reserva en los datos extraídos.")
        return

    logging.info(f"Manejando notificación urgente para la reserva PNR: {pnr}")

    try:
        from django.apps import apps

        Venta = apps.get_model("bookings", "Venta")
        venta = Venta.objects.select_related("cliente").get(localizador=pnr)
        cliente = venta.cliente
        logging.info(f"Venta y cliente ({cliente.get_nombre_completo()}) encontrados.")
    except Exception as e:
        # Check by class name or get_model dynamic reference
        if e.__class__.__name__ == "DoesNotExist" or "DoesNotExist" in str(type(e)):
            logging.error(f"No se encontró una venta con el PNR {pnr}.")
        else:
            logging.error(f"Error buscando la venta {pnr}: {e}")
        return

    if venta.google_calendar_event_id:
        try:
            from django.utils.module_loading import import_string

            update_calendar_event = import_string(
                "apps.bookings.services.calendar_service.update_calendar_event"
            )

            update_calendar_event(venta.google_calendar_event_id, extracted_data)
            logging.info(f"Evento de calendario {venta.google_calendar_event_id} actualizado.")
        except Exception as e:
            logging.error(f"No se pudo actualizar el evento del calendario: {e}")

    mensaje_notificacion = generate_whatsapp_notification(cliente, extracted_data)

    if cliente.telefono_principal:
        from apps.common.tasks import send_whatsapp_task

        send_whatsapp_task.delay(
            sender_id=cliente.telefono_principal,
            recipient_number=cliente.telefono_principal,
            message_text=mensaje_notificacion,
        )
    else:
        logging.warning(
            f"El cliente {cliente.get_nombre_completo()} no tiene un teléfono para notificar."
        )


# ============================================================================
# SECTION 4: TICKET NOTIFICATIONS
# ============================================================================


def notificar_boleto_procesado(boleto):
    """
    Notifica al cliente/admin cuando su boleto está listo.
    - WhatsApp al Admin con PDF (Twilio legacy)
    - WhatsApp al Cliente con PDF (Evolution/Meta API via Celery task)
    - Email al cliente (si existe)
    """
    agencia_nombre = "TravelHub"
    cliente = None
    agencia_id = None
    agencia = None

    if boleto.venta_asociada:
        venta = boleto.venta_asociada
        cliente = venta.cliente
        agencia = getattr(venta, "agencia", None)
        agencia_nombre = venta.agencia.nombre if venta.agencia else "TravelHub"
        agencia_id = venta.agencia.id if venta.agencia else None
    elif boleto.agencia:
        agencia = boleto.agencia
        agencia_nombre = boleto.agencia.nombre
        agencia_id = boleto.agencia.id

    datos = boleto.datos_parseados.get("normalized", {}) if boleto.datos_parseados else {}
    pnr = datos.get("reservation_code", boleto.localizador_pnr or "N/A")
    pasajero = datos.get("passenger_name", boleto.nombre_pasajero_procesado or "N/A")

    # URL del PDF
    pdf_url = ""
    try:
        if boleto.archivo_pdf_generado:
            try:
                pdf_url = boleto.archivo_pdf_generado.url
            except Exception:
                pdf_url = f"{settings.MEDIA_URL if 'http' in settings.MEDIA_URL else 'https://travelhub.travelinkeo.com' + settings.MEDIA_URL}{boleto.archivo_pdf_generado.name}"

            if pdf_url and not pdf_url.startswith("http"):
                pdf_url = f"https://travelhub.travelinkeo.com{pdf_url}"
    except Exception as e:
        logger.error(f"Error generando URL del PDF para boleto: {e}")

    # Configuración del canal de notificación (WhatsApp, Telegram o Ambos)
    canal = "both"
    if agencia and hasattr(agencia, "configuracion") and agencia.configuracion:
        canal = agencia.configuracion.canal_notificaciones_mailbot
        if not canal:
            canal = "both"

    admin_phone = getattr(settings, "ADMIN_WHATSAPP_NUMBER", "+584126080861")
    is_enabled = getattr(settings, "WHATSAPP_NOTIFICATIONS_ENABLED", False)

    # 1. NOTIFICACIÓN AL ADMIN
    mensaje_admin = f"""✈️ *Boleto Generado - {agencia_nombre}*

Estimado Administrador,

Se ha procesado un nuevo boleto de forma automática.

📋 *Detalles:*
• PNR: *{pnr}*
• Pasajero: {pasajero}
• Aerolínea: {boleto.aerolinea_emisora or "N/A"}
• Boleto: {boleto.numero_boleto}
"""
    if canal in ["whatsapp", "both"] and is_enabled and admin_phone:
        try:
            from apps.common.tasks.evolution import send_evolution_message_task

            send_evolution_message_task.delay(
                agencia_id=agencia_id,
                phone_number=admin_phone,
                text=mensaje_admin,
            )
            logger.info(f"Tarea WhatsApp Evolution encolada para Admin ({admin_phone})")
        except Exception as e:
            logger.error(f"Error encolando WhatsApp para Admin ({admin_phone}): {e}")

    if canal in ["telegram", "both"]:
        try:
            from apps.communications.services.telegram_unified import TelegramNotificationService

            if pdf_url:
                TelegramNotificationService.send_document(
                    file_path=pdf_url, caption=mensaje_admin, agencia=agencia
                )
            else:
                TelegramNotificationService.send_message(message=mensaje_admin, agencia=agencia)
            logger.info("Notificación de Telegram enviada al Admin")
        except Exception as e:
            logger.error(f"Error enviando Telegram al Admin: {e}")

    # 2. NOTIFICACIÓN AL CLIENTE
    if cliente:
        mensaje_cliente = f"""✈️ *¡Tu boleto está listo! - {agencia_nombre}*

Hola *{cliente.get_nombre_completo()}*,

Te informamos que hemos procesado tu boleto de avión con éxito.

📋 *Detalles de tu viaje:*
• Localizador PNR: *{pnr}*
• Pasajero: {pasajero}
• Aerolínea: {boleto.aerolinea_emisora or "N/A"}
• Nro Boleto: {boleto.numero_boleto or "N/A"}

Adjunto encontrarás tu boleto unificado en formato PDF.

¡Que disfrutes tu viaje!
_{agencia_nombre}_
"""
        # WhatsApp al Cliente
        if canal in ["whatsapp", "both"] and is_enabled and cliente.telefono_principal:
            try:
                from django.db import transaction

                from core.api import enviar_notificacion_whatsapp_task

                transaction.on_commit(
                    lambda: enviar_notificacion_whatsapp_task.delay(
                        numero_cliente=cliente.telefono_principal,
                        mensaje=mensaje_cliente,
                        email_cliente=cliente.email,
                        agencia_id=agencia_id,
                        media_url=pdf_url if pdf_url else None,
                        file_name=f"Boleto_{pasajero.replace('/', '_')}_{pnr}.pdf",
                    )
                )
                logger.info(f"Encolada tarea WhatsApp para cliente {cliente.get_nombre_completo()}")
            except Exception as e_celery:
                logger.error(f"Error encolando tarea de WhatsApp para cliente: {e_celery}")

        # Telegram al Cliente
        if canal in ["telegram", "both"] and getattr(cliente, "telegram_chat_id", None):
            try:
                from apps.communications.services.telegram_unified import (
                    TelegramNotificationService,
                )

                if pdf_url:
                    TelegramNotificationService.send_document(
                        file_path=pdf_url,
                        caption=mensaje_cliente,
                        chat_id=cliente.telegram_chat_id,
                        agencia=agencia,
                    )
                else:
                    TelegramNotificationService.send_message(
                        message=mensaje_cliente, chat_id=cliente.telegram_chat_id, agencia=agencia
                    )
                logger.info(
                    f"Notificación Telegram enviada a cliente {cliente.get_nombre_completo()}"
                )
            except Exception as e:
                logger.error(f"Error enviando Telegram al cliente: {e}")

    # Email al cliente
    if cliente and cliente.email:
        if "@sin-email.com" in cliente.email.lower():
            logger.info(
                f"🔕 Notificación omitida para email de marcador de posición: {cliente.email}"
            )
            return True

        try:
            enviar_email_generico(
                destinatario=cliente.email,
                asunto=f"Boleto Listo - PNR {pnr}",
                mensaje=f"Su boleto para {pasajero} está listo. PNR: {pnr}",
                from_email=agencia.email_principal if agencia else settings.DEFAULT_FROM_EMAIL,
                agencia=agencia,
            )
        except Exception as e:
            logger.error(f"Error enviando email: {e}")

    return True


def enviar_recordatorio_vuelo(boleto, horas_antes: int = 24):
    """
    Envía recordatorio X horas antes del vuelo
    """
    if not boleto.venta_asociada or not boleto.venta_asociada.cliente:
        return False

    venta = boleto.venta_asociada
    cliente = venta.cliente
    agencia = getattr(venta, "agencia", None)

    datos = boleto.datos_parseados.get("normalized", {}) if boleto.datos_parseados else {}
    pnr = datos.get("reservation_code", boleto.localizador_pnr or "N/A")
    pasajero = datos.get("passenger_name", boleto.nombre_pasajero_procesado or "N/A")

    vuelos = datos.get("flights", [])
    if not vuelos:
        return False

    primer_vuelo = vuelos[0]
    origen = primer_vuelo.get("origin", "N/A")
    destino = primer_vuelo.get("destination", "N/A")
    fecha = primer_vuelo.get("date", "N/A")
    hora = primer_vuelo.get("time", "N/A")

    if cliente.telefono_principal:
        mensaje = f"""⏰ *Recordatorio de Vuelo - TravelHub*

Estimado/a *{cliente.get_nombre_completo()}*,

Su vuelo sale en {horas_antes} horas.

✈️ *Detalles del Vuelo:*
• PNR: *{pnr}*
• Pasajero: {pasajero}
• Ruta: {origen} → {destino}
• Fecha: {fecha}
• Hora: {hora}
• Aerolínea: {boleto.aerolinea_emisora or "N/A"}

💡 *Recomendaciones:*
• Llegue al aeropuerto 3 horas antes
• Tenga su documento de identidad
• Verifique el peso de su equipaje

¡Buen viaje!

_TravelHub_"""

        try:
            from apps.common.tasks import send_whatsapp_task

            agencia_id = getattr(agencia, "pk", None) if agencia else None
            send_whatsapp_task.delay(
                sender_id=cliente.telefono_principal,
                recipient_number=cliente.telefono_principal,
                message_text=mensaje,
                agencia_id=agencia_id,
            )
        except Exception as e:
            logger.error(f"Error encolando recordatorio de vuelo: {e}")
        return True

    return False


# ============================================================================
# SECTION 5: ADMIN & SYSTEM ALERTS
# ============================================================================


def notificar_alerta_migratoria(check_instance):
    """
    Notifica a los agentes sobre alertas migratorias críticas vía Celery tasks.
    """
    from apps.common.tasks import send_telegram_task, send_whatsapp_task

    agencia_id = None
    agencia = None
    if getattr(check_instance, "venta", None):
        agencia = check_instance.venta.agencia
    elif getattr(check_instance, "pasajero", None) and getattr(
        check_instance.pasajero, "agencia", None
    ):
        agencia = check_instance.pasajero.agencia
    if agencia and hasattr(agencia, "pk"):
        agencia_id = agencia.pk

    whatsapp_msg = (
        f"⚠️ *ALERTA MIGRATORIA* ⚠️\n\n"
        f"Localizador: *{check_instance.localizador}*\n"
        f"Pasajero: {check_instance.pasajero_nombre}\n"
        f"Nivel: {check_instance.alert_level}\n\n"
        f"Resumen: {check_instance.summary}\n\n"
        f"Por favor, verifique los requisitos en el dashboard."
    )
    admin_phone = getattr(settings, "ADMIN_WHATSAPP_NUMBER", None)
    if admin_phone:
        send_whatsapp_task.delay(
            sender_id=admin_phone,
            recipient_number=admin_phone,
            message_text=whatsapp_msg,
            agencia_id=agencia_id,
        )

    telegram_msg = (
        f"⚠️ ALERTA MIGRATORIA\n\n"
        f"Localizador: {check_instance.localizador}\n"
        f"Pasajero: {check_instance.pasajero_nombre}\n"
        f"Nivel: {check_instance.alert_level}\n\n"
        f"{check_instance.summary}"
    )
    send_telegram_task.delay(message=telegram_msg, agencia_id=agencia_id)


class NotificationService:
    """
    SERVICIO CENTRAL DE NOTIFICACIONES (Legacy compatibility):
    Gestiona el envío de correos electrónicos profesionales,
    notificaciones push y mensajes de WhatsApp.
    """

    @staticmethod
    def enviar_reporte_pdf_email(agencia, email_destino, pdf_bytes, kpis):
        """
        Envía el reporte de conciliación consolidado por correo electrónico
        con el PDF adjunto directamente desde memoria.
        """
        subject = f"📊 Reporte de Conciliación Consolidado - {agencia.nombre}"

        context = {
            "agencia_nombre": agencia.nombre,
            "kpis": kpis,
            "color_primario": agencia.color_primario or "#10b981",
        }

        html_content = render_to_string("finance/emails/reconciliation_summary.html", context)
        text_content = strip_tags(html_content)

        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[email_destino],
        )
        email.attach_alternative(html_content, "text/html")

        filename = f"Reporte_Gestion_{agencia.nombre.replace(' ', '_')}.pdf"
        email.attach(filename, pdf_bytes.getvalue(), "application/pdf")

        try:
            email.send()
            logger.info(
                f"✅ Email de reporte enviado exitosamente a {email_destino} para {agencia.nombre}"
            )
            return True
        except Exception as e:
            logger.error(f"❌ Error enviando email de reporte a {email_destino}: {str(e)}")
            raise e

    @staticmethod
    def enviar_bienvenida_agencia(agencia, user):
        """
        Envía el correo de bienvenida a una nueva agencia.
        """
        subject = f"🚀 ¡Bienvenido a TravelHub! - {agencia.nombre} está lista"

        context = {
            "agencia_nombre": agencia.nombre,
            "admin_name": user.first_name or user.username,
            "admin_email": user.email,
            "subdominio": agencia.subdominio_slug,
            "color_primario": agencia.color_primario or "#3b82f6",
        }

        html_content = render_to_string("onboarding/welcome_email.html", context)
        text_content = strip_tags(html_content)

        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email],
        )
        email.attach_alternative(html_content, "text/html")

        try:
            email.send()
            logger.info(f"🚀 Email de bienvenida enviado a {user.email}")
            return True
        except Exception as e:
            logger.error(f"❌ Error enviando email de bienvenida: {str(e)}")
            return False

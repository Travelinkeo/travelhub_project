"""
Notification Router Unificado (P4-004)
======================================

Consolida todas las funciones de notificación dispersas en notification_dispatcher.py
en una sola clase con API limpia y extensible.

Reemplaza:
- NotificationDispatcher class
- notificar_confirmacion_pago()
- notificar_recordatorio_pago()
- notificar_confirmacion_venta()
- generate_whatsapp_notification()
- handle_urgent_notification()
- notificar_boleto_procesado()
- enviar_recordatorio_vuelo()
- notificar_alerta_migratoria()
- NotificationService class
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)


class NotificationEvent(str, Enum):
    """Eventos de notificación soportados"""

    # Ventas
    VENTA_CONFIRMADA = "venta_confirmada"
    VENTA_CANCELADA = "venta_cancelada"
    VENTA_MODIFICADA = "venta_modificada"

    # Pagos
    PAGO_CONFIRMADO = "pago_confirmado"
    PAGO_PENDIENTE = "pago_pendiente"
    RECORDATORIO_PAGO = "recordatorio_pago"

    # Boletos
    BOLETO_PROCESADO = "boleto_procesado"
    BOLETO_ERROR = "boleto_error"

    # Vuelos
    VUELO_CAMBIO = "vuelo_cambio"
    VUELO_CANCELADO = "vuelo_cancelado"
    RECORDATORIO_VUELO = "recordatorio_vuelo"

    # Alertas
    ALERTA_MIGRATORIA = "alerta_migratoria"
    ALERTA_SISTEMA = "alerta_sistema"

    # Onboarding
    BIENVENIDA_AGENCIA = "bienvenida_agencia"

    # Reportes
    REPORTE_PROGRAMADO = "reporte_programado"


class NotificationChannel(str, Enum):
    """Canales de notificación disponibles"""

    EMAIL = "email"
    WHATSAPP = "whatsapp"
    TELEGRAM = "telegram"
    PUSH = "push"


@dataclass
class NotificationRecipient:
    """Destinatario de la notificación"""

    email: str | None = None
    telefono: str | None = None
    telegram_chat_id: str | None = None
    push_token: str | None = None
    nombre: str = ""

    def get_for_channel(self, channel: NotificationChannel) -> str | None:
        mapping = {
            NotificationChannel.EMAIL: self.email,
            NotificationChannel.WHATSAPP: self.telefono,
            NotificationChannel.TELEGRAM: self.telegram_chat_id,
            NotificationChannel.PUSH: self.push_token,
        }
        return mapping.get(channel)


@dataclass
class NotificationContext:
    """Contexto para construir el mensaje"""

    event: NotificationEvent
    recipient: NotificationRecipient
    data: dict[str, Any] = field(default_factory=dict)
    agencia_id: int | None = None
    agencia_nombre: str = "TravelHub"

    def get(self, key: str, default=None):
        return self.data.get(key, default)


class NotificationChannelBase(ABC):
    """Canal base de notificación"""

    @abstractmethod
    def send(self, context: NotificationContext, message: str) -> bool:
        """Envía la notificación"""
        pass

    @abstractmethod
    def is_available(self, context: NotificationContext) -> bool:
        """Verifica si el canal está disponible"""
        pass


class EmailChannel(NotificationChannelBase):
    """Canal de email"""

    def is_available(self, context: NotificationContext) -> bool:
        email = context.recipient.get_for_channel(NotificationChannel.EMAIL)
        return bool(email and settings.EMAIL_HOST_USER)

    def send(self, context: NotificationContext, message: str) -> bool:
        try:
            email = context.recipient.get_for_channel(NotificationChannel.EMAIL)
            if not email:
                return False

            subject = self._get_subject(context)
            html_content = self._render_html(context, message)
            text_content = strip_tags(html_content)

            from_email = settings.DEFAULT_FROM_EMAIL
            if context.agencia_id:
                from apps.core.models import AgenciaConfiguracion

                config = AgenciaConfiguracion.objects.filter(agencia_id=context.agencia_id).first()
                if config and config.email_principal:
                    from_email = config.email_principal

            email_msg = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=from_email,
                to=[email],
            )
            email_msg.attach_alternative(html_content, "text/html")
            email_msg.send(fail_silently=False)
            return True
        except Exception as e:
            logger.error(f"Error enviando email: {e}")
            return False

    def _get_subject(self, context: NotificationContext) -> str:
        subjects = {
            NotificationEvent.VENTA_CONFIRMADA: f"✅ Venta confirmada - {context.data.get('localizador', '')}",
            NotificationEvent.PAGO_CONFIRMADO: f"💰 Pago confirmado - {context.data.get('localizador', '')}",
            NotificationEvent.RECORDATORIO_PAGO: f"⏰ Recordatorio de pago - {context.data.get('localizador', '')}",
            NotificationEvent.BOLETO_PROCESADO: f"✈️ Boleto listo - {context.data.get('localizador', '')}",
            NotificationEvent.VUELO_CAMBIO: f"🔄 Cambio en vuelo - {context.data.get('pnr', '')}",
            NotificationEvent.RECORDATORIO_VUELO: f"⏰ Recordatorio de vuelo - {context.data.get('pnr', '')}",
            NotificationEvent.ALERTA_MIGRATORIA: f"⚠️ Alerta migratoria - {context.data.get('localizador', '')}",
            NotificationEvent.BIENVENIDA_AGENCIA: "🚀 Bienvenido a TravelHub",
        }
        return subjects.get(context.event, f"Notificación TravelHub - {context.event.value}")

    def _render_html(self, context: NotificationContext, message: str) -> str:
        try:
            return render_to_string(
                "emails/notification.html",
                {
                    "message": message,
                    "agencia_nombre": context.agencia_nombre,
                    "color_primario": "#10b981",
                    "data": context.data,
                },
            )
        except Exception:
            return f"<p>{message}</p>"


class WhatsAppChannel(NotificationChannelBase):
    """Canal de WhatsApp (Evolution API)"""

    def is_available(self, context: NotificationContext) -> bool:
        phone = context.recipient.get_for_channel(NotificationChannel.WHATSAPP)
        if not phone:
            return False
        if not getattr(settings, "WHATSAPP_NOTIFICATIONS_ENABLED", False):
            return False
        if context.agencia_id:
            from apps.core.models import AgenciaConfiguracion

            config = AgenciaConfiguracion.objects.filter(agencia_id=context.agencia_id).first()
            if config and config.evolution_instance_name:
                return True
        return True

    def send(self, context: NotificationContext, message: str) -> bool:
        try:
            from apps.common.tasks import send_whatsapp_task

            phone = context.recipient.get_for_channel(NotificationChannel.WHATSAPP)
            if not phone:
                return False

            agencia_id = context.agencia_id
            send_whatsapp_task.delay(
                sender_id=phone,
                recipient_number=phone,
                message_text=message,
                agencia_id=agencia_id,
            )
            return True
        except Exception as e:
            logger.error(f"Error encolando WhatsApp: {e}")
            return False


class TelegramChannel(NotificationChannelBase):
    """Canal de Telegram"""

    def is_available(self, context: NotificationContext) -> bool:
        chat_id = context.recipient.get_for_channel(NotificationChannel.TELEGRAM)
        if chat_id:
            return True
        if context.agencia_id:
            from apps.core.models import AgenciaConfiguracion

            config = AgenciaConfiguracion.objects.filter(agencia_id=context.agencia_id).first()
            if config and config.telegram_chat_id:
                return True
        return bool(getattr(settings, "TELEGRAM_BOT_TOKEN", None)) and (
            bool(getattr(settings, "TELEGRAM_GROUP_ID", None))
            or bool(getattr(settings, "TELEGRAM_CHANNEL_ID", None))
        )

    def send(self, context: NotificationContext, message: str) -> bool:
        try:
            from apps.communications.services.telegram_unified import TelegramNotificationService

            chat_id = context.recipient.get_for_channel(NotificationChannel.TELEGRAM)
            if not chat_id and context.agencia_id:
                from apps.core.models import AgenciaConfiguracion

                config = AgenciaConfiguracion.objects.filter(agencia_id=context.agencia_id).first()
                if config:
                    chat_id = config.telegram_chat_id

            if not chat_id:
                return False

            agencia = None
            if context.agencia_id:
                from apps.core.models import Agencia

                try:
                    agencia = Agencia.objects.get(pk=context.agencia_id)
                except Agencia.DoesNotExist:
                    agencia = None

            TelegramNotificationService.send_message(
                message=message,
                chat_id=chat_id,
                parse_mode="HTML",
                agencia=agencia,
            )
            return True
        except Exception as e:
            logger.error(f"Error enviando Telegram: {e}")
            return False


class PushChannel(NotificationChannelBase):
    """Canal de Push Notifications (Web Push)"""

    def is_available(self, context: NotificationContext) -> bool:
        return bool(context.recipient.get_for_channel(NotificationChannel.PUSH))

    def send(self, context: NotificationContext, message: str) -> bool:
        try:
            from apps.communications.views.push_views import send_push_notification

            push_token = context.recipient.get_for_channel(NotificationChannel.PUSH)
            if not push_token:
                return False

            send_push_notification(
                push_token,
                {
                    "title": self._get_title(context),
                    "body": message,
                    "data": context.data,
                },
            )
            return True
        except Exception as e:
            logger.error(f"Error enviando push: {e}")
            return False

    def _get_title(self, context: NotificationContext) -> str:
        titles = {
            NotificationEvent.VENTA_CONFIRMADA: "Venta confirmada",
            NotificationEvent.PAGO_CONFIRMADO: "Pago confirmado",
            NotificationEvent.RECORDATORIO_PAGO: "Recordatorio de pago",
            NotificationEvent.BOLETO_PROCESADO: "Boleto listo",
            NotificationEvent.VUELO_CAMBIO: "Cambio en vuelo",
            NotificationEvent.RECORDATORIO_VUELO: "Recordatorio de vuelo",
            NotificationEvent.ALERTA_MIGRATORIA: "Alerta migratoria",
        }
        return titles.get(context.event, "TravelHub")


class NotificationRouter:
    """
    Router unificado de notificaciones.

    Punto de entrada único para todas las notificaciones del sistema.
    Maneja routing multi-canal, templates, y orquestación.
    """

    def __init__(self):
        self.channels: dict[NotificationChannel, NotificationChannelBase] = {
            NotificationChannel.EMAIL: EmailChannel(),
            NotificationChannel.WHATSAPP: WhatsAppChannel(),
            NotificationChannel.TELEGRAM: TelegramChannel(),
            NotificationChannel.PUSH: PushChannel(),
        }
        self._channel_priority = [
            NotificationChannel.WHATSAPP,
            NotificationChannel.EMAIL,
            NotificationChannel.TELEGRAM,
            NotificationChannel.PUSH,
        ]

    def notify(
        self, context: NotificationContext, channels: list[NotificationChannel] | None = None
    ) -> dict[NotificationChannel, bool]:
        """
        Envía notificación por los canales disponibles.

        Args:
            context: Contexto completo de la notificación
            channels: Canales específicos (None = todos disponibles)

        Returns:
            Dict con resultado por canal
        """
        results = {}
        target_channels = channels or self._channel_priority

        # Construir mensaje base
        message = self._build_message(context)

        for channel_enum in target_channels:
            channel = self.channels.get(channel_enum)
            if not channel:
                results[channel_enum] = False
                continue

            if not channel.is_available(context):
                logger.debug(
                    f"Canal {channel_enum.value} no disponible para notificación {context.event.value}"
                )
                results[channel_enum] = False
                continue

            try:
                success = channel.send(context, message)
                results[channel_enum] = success
                logger.info(
                    f"Notificación {context.event.value} via {channel_enum.value}: {'OK' if success else 'FAIL'}"
                )
            except Exception as e:
                logger.error(f"Error en canal {channel_enum.value}: {e}")
                results[channel_enum] = False

        return results

    def _build_message(self, context: NotificationContext) -> str:
        """Construye el mensaje según el evento"""
        builders = {
            NotificationEvent.VENTA_CONFIRMADA: self._build_venta_message,
            NotificationEvent.PAGO_CONFIRMADO: self._build_pago_message,
            NotificationEvent.RECORDATORIO_PAGO: self._build_recordatorio_pago_message,
            NotificationEvent.BOLETO_PROCESADO: self._build_boleto_message,
            NotificationEvent.VUELO_CAMBIO: self._build_vuelo_cambio_message,
            NotificationEvent.RECORDATORIO_VUELO: self._build_recordatorio_vuelo_message,
            NotificationEvent.ALERTA_MIGRATORIA: self._build_alerta_migratoria_message,
            NotificationEvent.BIENVENIDA_AGENCIA: self._build_bienvenida_message,
            NotificationEvent.VENTA_CANCELADA: self._build_venta_cancelada_message,
            NotificationEvent.BOLETO_ERROR: self._build_boleto_error_message,
        }

        builder = builders.get(context.event)
        if builder:
            return builder(context)

        # Fallback genérico
        return self._build_generic_message(context)

    # ========== Builders por evento ==========

    def _build_venta_message(self, context: NotificationContext) -> str:
        venta = context.data.get("venta")
        if not venta:
            return "Venta confirmada"

        localizador = getattr(venta, "localizador", "N/A")
        total = getattr(venta, "total_venta", getattr(venta, "monto_total", "N/A"))

        return (
            f"✅ *Venta Confirmada* - {context.agencia_nombre}\n\n"
            f"📋 Localizador: *{localizador}*\n"
            f"💰 Total: *{total}*\n\n"
            f"¡Gracias por confiar en {context.agencia_nombre}!"
        )

    def _build_pago_message(self, context: NotificationContext) -> str:
        venta = context.data.get("venta")
        if not venta:
            return "Pago confirmado"

        localizador = getattr(venta, "localizador", "N/A")
        monto = context.data.get("monto", "N/A")

        return (
            f"💰 *Pago Confirmado* - {context.agencia_nombre}\n\n"
            f"📋 Localizador: *{localizador}*\n"
            f"💵 Monto: *{monto}*\n\n"
            f"Gracias por tu pago."
        )

    def _build_recordatorio_pago_message(self, context: NotificationContext) -> str:
        venta = context.data.get("venta")
        if not venta:
            return "Recordatorio de pago"

        localizador = getattr(venta, "localizador", "N/A")
        saldo = getattr(venta, "saldo_pendiente", getattr(venta, "monto_venta_cliente", "N/A"))

        dias = context.data.get("dias", 3)

        return (
            f"⏰ *Recordatorio de Pago* - {context.agencia_nombre}\n\n"
            f"📋 Localizador: *{localizador}*\n"
            f"💳 Saldo pendiente: *{saldo}*\n\n"
            f"Quedan {dias} días para completar el pago.\n"
            f"Contacta a tu agente para más información."
        )

    def _build_boleto_message(self, context: NotificationContext) -> str:
        boleto = context.data.get("boleto")
        if not boleto:
            return "Tu boleto está listo"

        datos = boleto.datos_parseados.get("normalized", {}) if boleto.datos_parseados else {}
        pnr = datos.get("reservation_code", boleto.localizador_pnr or "N/A")
        pasajero = datos.get("passenger_name", boleto.nombre_pasajero_procesado or "N/A")
        aerolinea = boleto.aerolinea_emisora or "N/A"

        return (
            f"✈️ *¡Tu boleto está listo!* - {context.agencia_nombre}\n\n"
            f"Hola *{context.recipient.nombre}*,\n\n"
            f"📋 *Detalles de tu viaje:*\n"
            f"• Localizador PNR: *{pnr}*\n"
            f"• Pasajero: {pasajero}\n"
            f"• Aerolínea: {aerolinea}\n"
            f"• Nro Boleto: {boleto.numero_boleto or 'N/A'}\n\n"
            f"Adjunto encontrarás tu boleto unificado en formato PDF.\n\n"
            f"¡Que disfrutes tu viaje!\n_{context.agencia_nombre}_"
        )

    def _build_vuelo_cambio_message(self, context: NotificationContext) -> str:
        datos = context.data.get("datos_cambio", {})
        pnr = datos.get("pnr", "N/A")
        aerolinea = datos.get("aerolinea", "N/A")
        vuelo_ant = datos.get("vuelo_antiguo", {})
        vuelo_nuevo = datos.get("vuelo_nuevo", {})

        return (
            f"🔄 *Cambio en tu Vuelo* - {context.agencia_nombre}\n\n"
            f"Hola *{context.recipient.nombre}*,\n\n"
            f"Te informamos un cambio urgente en tu itinerario:\n\n"
            f"📋 *Reserva:* {pnr} ({aerolinea})\n\n"
            f"✈️ *Vuelo Original:*\n"
            f"• Fecha: {vuelo_ant.get('fecha', 'N/A')}\n"
            f"• Hora: {vuelo_ant.get('hora_salida', 'N/A')}\n\n"
            f"🆕 *NUEVO Vuelo:*\n"
            f"• Fecha: {vuelo_nuevo.get('fecha', 'N/A')}\n"
            f"• Hora: {vuelo_nuevo.get('hora_salida', 'N/A')}\n\n"
            f"Tu reserva está confirmada. Tu calendario se actualizó automáticamente.\n\n"
            f"¿Dudas? Respondé a este mensaje.\n\n_{context.agencia_nombre}_"
        )

    def _build_recordatorio_vuelo_message(self, context: NotificationContext) -> str:
        boleto = context.data.get("boleto")
        if not boleto:
            return "Recordatorio de vuelo"

        datos = boleto.datos_parseados.get("normalized", {}) if boleto.datos_parseados else {}
        pnr = datos.get("reservation_code", boleto.localizador_pnr or "N/A")
        pasajero = datos.get("passenger_name", boleto.nombre_pasajero_procesado or "N/A")
        vuelos = datos.get("flights", [])
        primer_vuelo = vuelos[0] if vuelos else {}
        origen = primer_vuelo.get("origin", "N/A")
        destino = primer_vuelo.get("destination", "N/A")
        fecha = primer_vuelo.get("date", "N/A")
        hora = primer_vuelo.get("time", "N/A")
        aerolinea = boleto.aerolinea_emisora or "N/A"
        horas_antes = context.data.get("horas_antes", 24)

        return (
            f"⏰ *Recordatorio de Vuelo* - {context.agencia_nombre}\n\n"
            f"Estimado/a *{context.recipient.nombre}*,\n\n"
            f"Su vuelo sale en *{horas_antes} horas*.\n\n"
            f"✈️ *Detalles:*\n"
            f"• PNR: *{pnr}*\n"
            f"• Pasajero: {pasajero}\n"
            f"• Ruta: {origen} → {destino}\n"
            f"• Fecha: {fecha}\n"
            f"• Hora: {hora}\n"
            f"• Aerolínea: {aerolinea}\n\n"
            f"💡 *Recomendaciones:*\n"
            f"• Llegue al aeropuerto 3 horas antes\n"
            f"• Tenga su documento de identidad\n"
            f"• Verifique el peso de su equipaje\n\n"
            f"¡Buen viaje!\n\n_{context.agencia_nombre}_"
        )

    def _build_alerta_migratoria_message(self, context: NotificationContext) -> str:
        check = context.data.get("check")
        if not check:
            return "Alerta migratoria"

        return (
            f"⚠️ *ALERTA MIGRATORIA* ⚠️\n\n"
            f"Localizador: *{check.localizador}*\n"
            f"Pasajero: {check.pasajero_nombre}\n"
            f"Nivel: {check.alert_level}\n\n"
            f"Resumen: {check.summary}\n\n"
            f"Por favor, verifique los requisitos en el dashboard."
        )

    def _build_bienvenida_message(self, context: NotificationContext) -> str:
        return (
            f"🚀 *¡Bienvenido a TravelHub!*\n\n"
            f"Hola *{context.recipient.nombre}*,\n\n"
            f"Tu agencia *{context.agencia_nombre}* ya está lista para operar.\n\n"
            f"🌐 Subdominio: {context.data.get('subdominio', 'N/A')}\n"
            f"🎨 Color: {context.data.get('color', '#10b981')}\n\n"
            f"¡Empecemos a volar!\n\n_{context.agencia_nombre}_"
        )

    def _build_venta_cancelada_message(self, context: NotificationContext) -> str:
        venta = context.data.get("venta")
        if not venta:
            return "Venta cancelada"

        localizador = getattr(venta, "localizador", "N/A")
        motivo = context.data.get("motivo", "No especificado")

        return (
            f"❌ *Venta Cancelada* - {context.agencia_nombre}\n\n"
            f"📋 Localizador: *{localizador}*\n"
            f"📝 Motivo: {motivo}\n\n"
            f"Si tienes dudas, contacta a tu agente."
        )

    def _build_boleto_error_message(self, context: NotificationContext) -> str:
        boleto = context.data.get("boleto")
        error = context.data.get("error", "Error desconocido")

        pnr = "N/A"
        if boleto:
            datos = boleto.datos_parseados.get("normalized", {}) if boleto.datos_parseados else {}
            pnr = datos.get("reservation_code", boleto.localizador_pnr or "N/A")

        return (
            f"⚠️ *Error Procesando Boleto* - {context.agencia_nombre}\n\n"
            f"PNR: *{pnr}*\n"
            f"Error: {error}\n\n"
            f"Por favor, revisa manualmente o contacta a soporte."
        )

    def _build_generic_message(self, context: NotificationContext) -> str:
        return (
            f"📢 *{context.event.value.replace('_', ' ').title()}* - {context.agencia_nombre}\n\n"
            f"{context.data}"
        )


# Instancia global singleton
notification_router = NotificationRouter()


# =============================================================================
# FUNCIONES DE COMPATIBILIDAD (Legacy)
# =============================================================================


def notificar_confirmacion_pago(pago_venta):
    """Legacy: notificar_confirmacion_pago"""

    venta = getattr(pago_venta, "venta", None)
    if not venta:
        return

    cliente = getattr(venta, "cliente", None)
    agencia = getattr(venta, "agencia", None)

    if not cliente:
        return

    recipient = NotificationRecipient(
        email=cliente.email,
        telefono=getattr(cliente, "telefono_principal", None),
        telegram_chat_id=getattr(cliente, "telegram_chat_id", None),
        nombre=cliente.get_nombre_completo()
        if hasattr(cliente, "get_nombre_completo")
        else str(cliente),
    )

    context = NotificationContext(
        event=NotificationEvent.PAGO_CONFIRMADO,
        recipient=recipient,
        data={"venta": venta, "monto": getattr(pago_venta, "monto", None)},
        agencia_id=agencia.id if agencia else None,
        agencia_nombre=agencia.nombre if agencia else "TravelHub",
    )

    notification_router.notify(context)


def notificar_recordatorio_pago(venta) -> dict[str, bool]:
    """Legacy: notificar_recordatorio_pago"""
    cliente = getattr(venta, "cliente", None)
    agencia = getattr(venta, "agencia", None)

    if not cliente:
        return {"email": False, "whatsapp": False}

    recipient = NotificationRecipient(
        email=cliente.email,
        telefono=getattr(cliente, "telefono_principal", None),
        telegram_chat_id=getattr(cliente, "telegram_chat_id", None),
        nombre=cliente.get_nombre_completo()
        if hasattr(cliente, "get_nombre_completo")
        else str(cliente),
    )

    context = NotificationContext(
        event=NotificationEvent.RECORDATORIO_PAGO,
        recipient=recipient,
        data={"venta": venta, "dias": 3},
        agencia_id=agencia.id if agencia else None,
        agencia_nombre=agencia.nombre if agencia else "TravelHub",
    )

    results = notification_router.notify(context)
    return {
        "email": results.get(NotificationChannel.EMAIL, False),
        "whatsapp": results.get(NotificationChannel.WHATSAPP, False),
    }


def notificar_confirmacion_venta(venta):
    """Legacy: notificar_confirmacion_venta"""
    cliente = getattr(venta, "cliente", None)
    agencia = getattr(venta, "agencia", None)

    if not cliente:
        return

    recipient = NotificationRecipient(
        email=cliente.email,
        telefono=getattr(cliente, "telefono_principal", None),
        telegram_chat_id=getattr(cliente, "telegram_chat_id", None),
        nombre=cliente.get_nombre_completo()
        if hasattr(cliente, "get_nombre_completo")
        else str(cliente),
    )

    context = NotificationContext(
        event=NotificationEvent.VENTA_CONFIRMADA,
        recipient=recipient,
        data={"venta": venta},
        agencia_id=agencia.id if agencia else None,
        agencia_nombre=agencia.nombre if agencia else "TravelHub",
    )

    notification_router.notify(context)


def notificar_boleto_procesado(boleto):
    """Legacy: notificar_boleto_procesado"""
    cliente = None
    agencia = None
    agencia_nombre = "TravelHub"
    agencia_id = None

    if boleto.venta_asociada:
        venta = boleto.venta_asociada
        cliente = venta.cliente
        agencia = getattr(venta, "agencia", None)
        agencia_nombre = getattr(agencia, "nombre", "TravelHub") if agencia else "TravelHub"
        agencia_id = agencia.id if agencia else None
    elif boleto.agencia:
        agencia = boleto.agencia
        agencia_nombre = agencia.nombre
        agencia_id = agencia.id

    if not cliente:
        logger.warning(f"Boleto {boleto.id} sin cliente para notificar")
        return

    recipient = NotificationRecipient(
        email=cliente.email,
        telefono=getattr(cliente, "telefono_principal", None),
        telegram_chat_id=getattr(cliente, "telegram_chat_id", None),
        nombre=cliente.get_nombre_completo()
        if hasattr(cliente, "get_nombre_completo")
        else str(cliente),
    )

    context = NotificationContext(
        event=NotificationEvent.BOLETO_PROCESADO,
        recipient=recipient,
        data={"boleto": boleto},
        agencia_id=agencia_id,
        agencia_nombre=agencia_nombre,
    )

    notification_router.notify(context)


def notificar_alerta_migratoria(check_instance):
    """Legacy: notificar_alerta_migratoria"""
    agencia = None
    agencia_id = None

    if getattr(check_instance, "venta", None):
        agencia = check_instance.venta.agencia
    elif getattr(check_instance, "pasajero", None) and getattr(
        check_instance.pasajero, "agencia", None
    ):
        agencia = check_instance.pasajero.agencia

    if agencia and hasattr(agencia, "pk"):
        agencia_id = agencia.pk

    admin_phone = getattr(settings, "ADMIN_WHATSAPP_NUMBER", None)
    if admin_phone:
        admin_recipient = NotificationRecipient(telefono=admin_phone, nombre="Admin")
        admin_context = NotificationContext(
            event=NotificationEvent.ALERTA_MIGRATORIA,
            recipient=admin_recipient,
            data={"check": check_instance},
            agencia_id=agencia_id,
            agencia_nombre=agencia.nombre if agencia else "TravelHub",
        )
        notification_router.notify(admin_context, channels=[NotificationChannel.WHATSAPP])

    if agencia_id:
        recipient = NotificationRecipient(nombre="Agencia")
        context = NotificationContext(
            event=NotificationEvent.ALERTA_MIGRATORIA,
            recipient=recipient,
            data={"check": check_instance},
            agencia_id=agencia_id,
            agencia_nombre=agencia.nombre if agencia else "TravelHub",
        )
        notification_router.notify(context, channels=[NotificationChannel.TELEGRAM])


# Export
__all__ = [
    "NotificationRouter",
    "NotificationEvent",
    "NotificationChannel",
    "NotificationRecipient",
    "NotificationContext",
    "notification_router",
    # Legacy compat
    "notificar_confirmacion_pago",
    "notificar_recordatorio_pago",
    "notificar_confirmacion_venta",
    "notificar_boleto_procesado",
    "notificar_alerta_migratoria",
]

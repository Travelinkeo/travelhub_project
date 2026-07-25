"""
Notification Manager (Unified)
Gestor unificado de notificaciones multi-canal con:
- Preferencias de usuario
- Plantillas personalizables
- Retry logic con backoff exponencial
- Logging y auditoría
- Rate limiting por canal
"""

import logging
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from django.db.models import Q
from django.utils import timezone

from apps.communications.models import NotificationLog, NotificationPreference, NotificationTemplate

logger = logging.getLogger(__name__)


@dataclass
class NotificationContext:
    """Contexto de datos para renderizar plantillas"""

    event_type: str
    recipient: str
    agency_id: int | None = None
    user_id: int | None = None
    data: dict[str, Any] = None
    content_type: str | None = None
    object_id: str | None = None

    def __post_init__(self):
        if self.data is None:
            self.data = {}


class NotificationManager:
    """
    Gestor centralizado de notificaciones.
    Usa patrón Strategy para seleccionar canal según preferencias.
    """

    # Rate limits por canal (mensajes por minuto)
    RATE_LIMITS = {
        "email": 60,
        "whatsapp": 30,
        "sms": 20,
        "push": 100,
        "in_app": 100,
        "slack": 60,
        "teams": 60,
    }

    # Retry config
    MAX_RETRIES = 3
    RETRY_DELAYS = [30, 90, 270]  # segundos (backoff exponencial)

    def __init__(self):
        # __init__: Método de inicialización de la clase.
        self.channels = self._init_channels()

    def _init_channels(self) -> dict[str, Any]:
        """Inicializa los canales disponibles"""
        from apps.communications.services.notification_dispatcher import (
            EmailChannel,
            WhatsAppChannel,
        )
        from apps.communications.services.slack_channel import SlackChannel, TeamsChannel

        return {
            "email": EmailChannel(),
            "whatsapp": WhatsAppChannel(),
            "slack": SlackChannel(),
            "teams": TeamsChannel(),
        }

    def send(self, context: NotificationContext, force_channel: str | None = None) -> bool:
        """
        Envía una notificación según las preferencias del usuario.

        Args:
            context: Contexto con datos de la notificación
            force_channel: Si se especifica, usa este canal ignorando preferencias

        Returns:
            True si se envió al menos una notificación exitosamente
        """
        if force_channel:
            channels_to_use = [force_channel]
        else:
            channels_to_use = self._get_preferred_channels(context)

        if not channels_to_use:
            logger.warning(f"No channels configured for event {context.event_type}")
            return False

        # Check rate limits
        for channel in list(channels_to_use):
            if not self._check_rate_limit(channel):
                logger.warning(f"Rate limit exceeded for {channel}")
                channels_to_use.remove(channel)

        if not channels_to_use:
            logger.warning("All channels rate-limited")
            return False

        # Get template
        template = self._get_template(context.event_type, channels_to_use[0])
        if not template:
            logger.error(f"No template found for {context.event_type}")
            return False

        # Render template
        rendered = template.render(context.data)

        sent_count = 0
        for channel_name in channels_to_use:
            success = self._send_via_channel(
                channel=channel_name,
                recipient=context.recipient,
                subject=rendered["subject"],
                body=rendered["body"],
                html=rendered["html"],
                context=context,
            )
            if success:
                sent_count += 1

        return sent_count > 0

    def send_bulk(
        self,
        event_type: str,
        recipients: list[str],
        data: dict[str, Any],
        agency_id: int | None = None,
    ) -> dict[str, int]:
        """
        Envía notificaciones en bulk a múltiples destinatarios.
        Útil para notificaciones masivas (ej: promos, alertas).

        Returns:
            Dict con conteo de enviados/fallidos
        """
        results = {"sent": 0, "failed": 0}

        for recipient in recipients:
            context = NotificationContext(
                event_type=event_type,
                recipient=recipient,
                agency_id=agency_id,
                data=data,
            )
            if self.send(context):
                results["sent"] += 1
            else:
                results["failed"] += 1

        return results

    def _get_preferred_channels(self, context: NotificationContext) -> list[str]:
        """Obtiene los canales preferidos del usuario para este evento"""
        if not context.user_id:
            # Si no hay usuario, usar canales por defecto
            return ["email", "in_app"]

        preferences = NotificationPreference.objects.filter(
            user_id=context.user_id,
            event_type=context.event_type,
            enabled=True,
        )

        if context.agency_id:
            preferences = preferences.filter(
                Q(agencia_id=context.agency_id) | Q(agencia__isnull=True)
            )

        # Priorizar por orden: whatsapp > email > in_app > slack > teams
        channel_priority = {
            "whatsapp": 1,
            "email": 2,
            "in_app": 3,
            "sms": 4,
            "push": 5,
            "slack": 6,
            "teams": 7,
        }
        channels = sorted(
            {p.channel for p in preferences},
            key=lambda c: channel_priority.get(c, 99),
        )

        return channels or ["in_app"]  # Fallback a in-app

    def _get_template(
        self, event_type: str, channel: str, language: str = "es"
    ) -> NotificationTemplate | None:
        """Obtiene la plantilla adecuada"""
        # Intentar plantilla personalizada por agencia
        template = (
            NotificationTemplate.objects.filter(
                event_type=event_type,
                channel=channel,
                language=language,
                is_active=True,
            )
            .order_by("-is_default", "-updated_at")
            .first()
        )

        if not template:
            logger.error(f"No template for {event_type}/{channel}/{language}")

        return template

    def _send_via_channel(
        self,
        channel: str,
        recipient: str,
        subject: str,
        body: str,
        html: str,
        context: NotificationContext,
    ) -> bool:
        """Envía notificación por un canal específico con retry logic"""
        log_entry = self._create_log(
            event_type=context.event_type,
            channel=channel,
            recipient=recipient,
            subject=subject,
            body=body,
            status="pending",
            context=context,
        )

        try:
            channel_obj = self.channels.get(channel)
            if not channel_obj:
                raise ValueError(f"Channel {channel} not available")

            success = channel_obj.send(
                recipient=recipient,
                message=body,
                subject=subject,
                html=html,
                agencia_id=context.agency_id,
            )

            if success:
                log_entry.status = "sent"
                log_entry.sent_at = timezone.now()
                log_entry.save(update_fields=["status", "sent_at", "updated_at"])
                logger.info(f"Notification sent via {channel} to {recipient}")
                return True
            else:
                raise Exception("Channel returned False")

        except Exception as e:
            logger.error(f"Error sending via {channel}: {e}")
            log_entry.status = "failed"
            log_entry.error_message = str(e)
            log_entry.retry_count += 1

            if log_entry.retry_count < self.MAX_RETRIES:
                log_entry.status = "retrying"
                log_entry.save(
                    update_fields=["status", "error_message", "retry_count", "updated_at"]
                )
                # Schedule retry (implementar con Celery beat)
                # self._schedule_retry(log_entry)
            else:
                log_entry.save(
                    update_fields=["status", "error_message", "retry_count", "updated_at"]
                )

            return False

    def _create_log(
        self,
        event_type: str,
        channel: str,
        recipient: str,
        subject: str,
        body: str,
        status: str,
        context: NotificationContext,
    ) -> NotificationLog:
        """Crea entrada de log para auditing"""
        return NotificationLog.objects.create(
            event_type=event_type,
            channel=channel,
            recipient=recipient,
            subject=subject,
            body=body,
            status=status,
            agencia_id=context.agency_id,
            user_id=context.user_id,
            content_type=context.content_type,
            object_id=context.object_id,
        )

    def _check_rate_limit(self, channel: str) -> bool:
        """Verifica rate limit para un canal"""
        from django.core.cache import cache

        limit = self.RATE_LIMITS.get(channel, 60)
        key = f"rate_limit:{channel}:{timezone.now().minute}"

        current = cache.get(key, 0)
        if current >= limit:
            return False

        cache.set(key, current + 1, 60)  # Expira en 60 segundos
        return True

    def get_stats(self, days: int = 7) -> dict[str, Any]:
        """
        Obtiene estadísticas de notificaciones de los últimos N días.
        """
        from django.db.models import Count

        since = timezone.now() - timedelta(days=days)

        logs = NotificationLog.objects.filter(created_at__gte=since)

        stats = {
            "total": logs.count(),
            "by_status": dict(logs.values_list("status").annotate(Count("id"))),
            "by_channel": dict(logs.values_list("channel").annotate(Count("id"))),
            "by_event": dict(logs.values("event_type").annotate(count=Count("id"))),
            "failed": logs.filter(status="failed").count(),
            "success_rate": 0,
        }

        if stats["total"] > 0:
            stats["success_rate"] = logs.filter(status="sent").count() / stats["total"] * 100

        return stats


# ============================================================================
# Helper functions para uso directo (backward compatibility)
# ============================================================================


def send_notification(
    event_type: str,
    recipient: str,
    data: dict,
    agency_id: int | None = None,
    user_id: int | None = None,
    force_channel: str | None = None,
) -> bool:
    """
    Función helper para enviar notificaciones fácilmente.

    Ejemplo:
        send_notification(
            event_type="venta_creada",
            recipient="cliente@email.com",
            data={
                "cliente_nombre": "Juan Pérez",
                "venta_id": "123",
                "total": "1500.00",
                "moneda": "USD",
            },
            agency_id=1,
        )
    """
    context = NotificationContext(
        event_type=event_type,
        recipient=recipient,
        agency_id=agency_id,
        user_id=user_id,
        data=data,
    )

    manager = NotificationManager()
    return manager.send(context, force_channel=force_channel)


def send_bulk_notification(
    event_type: str,
    recipients: list[str],
    data: dict,
    agency_id: int | None = None,
) -> dict[str, int]:
    """
    Función helper para envío masivo.

    Ejemplo:
        send_bulk_notification(
            event_type="promo_verano",
            recipients=["a@x.com", "b@y.com"],
            data={"descuento": "20%", "vigencia": "30 días"},
        )
    """
    manager = NotificationManager()
    return manager.send_bulk(event_type, recipients, data, agency_id)


def get_notification_stats(days: int = 7) -> dict[str, Any]:
    """Obtiene estadísticas de notificaciones"""
    manager = NotificationManager()
    return manager.get_stats(days)

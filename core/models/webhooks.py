"""
Webhooks para notificaciones en tiempo real de eventos de TravelHub.

Las agencias pueden registrar URLs para recibir notificaciones
cuando ocurran eventos como ventas, pagos, etc.
"""

import hashlib
import hmac
import logging
import secrets

from django.db import models
from django.utils import timezone

logger = logging.getLogger(__name__)


class WebhookEvent(models.TextChoices):
    """Eventos disponibles para webhooks."""

    VENTA_CREADA = "venta.creada", "Venta Creada"
    VENTA_ACTUALIZADA = "venta.actualizada", "Venta Actualizada"
    VENTA_ANULADA = "venta.anulada", "Venta Anulada"
    PAGO_CONFIRMADO = "pago.confirmado", "Pago Confirmado"
    PAGO_PENDIENTE = "pago.pendiente", "Pago Pendiente"
    BOLETO_IMPORTADO = "boleto.importado", "Boleto Importado"
    CLIENTE_CREADO = "cliente.creado", "Cliente Creado"
    COTIZACION_ENVIADA = "cotizacion.enviada", "Cotización Enviada"
    COTIZACION_APROBADA = "cotizacion.aprobada", "Cotización Aprobada"
    FACTURA_GENERADA = "factura.generada", "Factura Generada"
    NOTIFICACION_ENVIADA = "notificacion.enviada", "Notificación Enviada"


class Webhook(models.Model):
    """
    Endpoint webhook registrado por una agencia.

    Cada webhook tiene un secret para firmar los payloads
    y verificar la autenticidad.
    """

    agencia = models.ForeignKey(
        "core.Agencia",
        on_delete=models.CASCADE,
        related_name="webhooks",
        help_text="Agencia propietaria del webhook",
    )
    url = models.URLField(
        max_length=500,
        help_text="URL que recibirá las notificaciones POST",
    )
    events = models.JSONField(
        default=list,
        blank=True,
        help_text="Lista de eventos a escuchar (EJ: ['venta.creada', 'pago.confirmado'])",
    )
    secret = models.CharField(
        max_length=64,
        editable=False,
        help_text="Secret para firmar payloads (HMAC-SHA256)",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Pausar/reanudar sin eliminar",
    )
    description = models.CharField(
        max_length=200,
        blank=True,
        default="",
        help_text="Descripción del webhook",
    )
    # Estadísticas
    last_triggered_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Último intento de envío",
    )
    last_success_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Último envío exitoso",
    )
    failure_count = models.PositiveIntegerField(
        default=0,
        help_text="Contador de fallos consecutivos",
    )
    total_deliveries = models.PositiveIntegerField(
        default=0,
        help_text="Total de entregas exitosas",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        """Meta definición del modelo."""
        verbose_name = "Webhook"
        verbose_name_plural = "Webhooks"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["agencia", "is_active"], name="idx_webhook_agencia"),
        ]

    def __str__(self):
        return f"{self.url} ({', '.join(self.events[:3])})"

    def save(self, *args, **kwargs):
        """Método: save."""
        if not self.secret:
            self.secret = secrets.token_hex(32)
        super().save(*args, **kwargs)

    def sign_payload(self, payload_bytes: bytes) -> str:
        """Genera firma HMAC-SHA256 del payload."""
        return hmac.new(self.secret.encode(), payload_bytes, hashlib.sha256).hexdigest()

    def matches_event(self, event_type: str) -> bool:
        """Verifica si este webhook escucha el evento dado."""
        if not self.events:
            return True  # Sin filtro = todos los eventos
        return event_type in self.events

    def record_success(self):
        """Registra un envío exitoso."""
        self.last_success_at = timezone.now()
        self.last_triggered_at = timezone.now()
        self.failure_count = 0
        self.total_deliveries += 1
        self.save(
            update_fields=[
                "last_success_at",
                "last_triggered_at",
                "failure_count",
                "total_deliveries",
            ]
        )

    def record_failure(self):
        """Registra un fallo. Desactiva después de 10 fallos consecutivos."""
        self.last_triggered_at = timezone.now()
        self.failure_count += 1
        if self.failure_count >= 10:
            self.is_active = False
            logger.warning(f"Webhook desactivado por 10 fallos consecutivos: {self.url}")
        self.save(
            update_fields=[
                "last_triggered_at",
                "failure_count",
                "is_active",
            ]
        )


class WebhookDelivery(models.Model):
    """
    Registro de cada intento de entrega de webhook.
    Útil para debugging y auditoría.
    """

    webhook = models.ForeignKey(
        Webhook,
        on_delete=models.CASCADE,
        related_name="deliveries",
    )
    event_type = models.CharField(max_length=50)
    payload = models.JSONField(
        help_text="Payload enviado al webhook",
    )
    response_status = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="HTTP status code de la respuesta",
    )
    response_body = models.TextField(
        blank=True,
        default="",
        max_length=1000,
        help_text="Primeros 1000 chars de la respuesta",
    )
    success = models.BooleanField(default=False)
    error_message = models.TextField(blank=True, default="")
    duration_ms = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Duración del request en milisegundos",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        """Meta definición del modelo."""
        verbose_name = "Webhook Delivery"
        verbose_name_plural = "Webhook Deliveries"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["webhook", "success"], name="idx_webhook_del_success"),
            models.Index(fields=["created_at"], name="idx_webhook_del_date"),
        ]

    def __str__(self):
        status = "✅" if self.success else "❌"
        return f"{status} {self.event_type} → {self.webhook.url}"

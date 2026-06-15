import uuid
from datetime import timedelta

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

from core.api import AgenciaMixin


class LinkDePago(AgenciaMixin, models.Model):
    """
    Contrato de seguridad para pagos externos (B2C).
    Genera una URL única e inexpugnable para que el cliente pague su itinerario.
    """

    class EstadoPago(models.TextChoices):
        PENDIENTE = "PEN", "Pendiente"
        EN_REVISION = "REV", "En Revisión (Zelle/Transf)"
        PAGADO = "PAG", "Pagado Exitosamente"
        EXPIRADO = "EXP", "Expirado"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    venta = models.ForeignKey(
        "bookings.Venta",
        on_delete=models.CASCADE,
        unique=True,
        verbose_name=_("Venta"),
        null=True,
        blank=True,
    )

    monto_total = models.DecimalField(max_digits=12, decimal_places=2)
    moneda = models.CharField(max_length=3, default="USD")

    estado = models.CharField(
        max_length=3, choices=EstadoPago.choices, default=EstadoPago.PENDIENTE
    )

    # Tracking de Zelle/Transferencias manuales
    referencia_pago = models.CharField(max_length=100, blank=True, null=True)
    comprobante_imagen = models.ImageField(upload_to="comprobantes_pago/", blank=True, null=True)

    creado_en = models.DateTimeField(auto_now_add=True)
    expira_en = models.DateTimeField()

    def save(self, *args, **kwargs):
        if not self.expira_en:
            # Los links mágicos expiran en 24 horas por defecto para crear urgencia
            self.expira_en = timezone.now() + timedelta(hours=24)
        super().save(*args, **kwargs)

    @property
    def esta_activo(self):
        return self.estado == self.EstadoPago.PENDIENTE and timezone.now() < self.expira_en

    def __str__(self):
        loc = self.venta.localizador if self.venta else "N/A"
        return f"Link {self.id} - Venta {loc} ({self.estado})"

    class Meta:
        indexes = [
            models.Index(fields=["estado"], name="idx_linkpago_estado"),
        ]

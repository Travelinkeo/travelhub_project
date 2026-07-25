from django.conf import settings
from django.db import models

from core.models.base import AgenciaMixin


class HistorialCambioBoleto(AgenciaMixin, models.Model):
    """Función: HistorialCambioBoleto."""
    TIPO_CAMBIO_CHOICES = [
        ("PRE", "Precio cambiado"),
        ("EST", "Estado cambiado"),
        ("RUT", "Ruta cambiada"),
        ("FEC", "Fecha cambiada"),
        ("PAX", "Pasajero cambiado"),
        ("OTR", "Otro"),
    ]

    boleto = models.ForeignKey(
        "bookings.BoletoImportado", on_delete=models.CASCADE, related_name="historial_cambios"
    )
    tipo_cambio = models.CharField(max_length=3, choices=TIPO_CAMBIO_CHOICES)
    descripcion = models.TextField(blank=True)
    valor_anterior = models.CharField(max_length=255, blank=True)
    valor_nuevo = models.CharField(max_length=255, blank=True)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    fecha_cambio = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha_cambio"]
        """Función: Meta."""
        verbose_name = "Historial de Cambio"
        verbose_name_plural = "Historial de Cambios"

    def __str__(self):
        return f"{self.get_tipo_cambio_display()} - {self.boleto}"


class AnulacionBoleto(AgenciaMixin, models.Model):
    """Función: AnulacionBoleto."""
    TIPO_ANULACION_CHOICES = [
        ("VOL", "Voluntaria"),
        ("INV", "Involutaria"),
    ]
    ESTADO_CHOICES = [
        ("SOL", "Solicitada"),
        ("APR", "Aprobada"),
        ("REC", "Rechazada"),
        ("REE", "Reembolsada"),
    ]

    boleto = models.ForeignKey(
        "bookings.BoletoImportado", on_delete=models.CASCADE, related_name="anulaciones"
    )
    tipo_anulacion = models.CharField(max_length=3, choices=TIPO_ANULACION_CHOICES, default="VOL")
    motivo = models.TextField(blank=True)
    monto_original = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    penalidad_aerolinea = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    fee_agencia = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    monto_reembolso = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    estado = models.CharField(max_length=3, choices=ESTADO_CHOICES, default="SOL")
    solicitado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="anulaciones_solicitadas",
    )
    aprobado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="anulaciones_aprobadas",
    )
    notas = models.TextField(blank=True)
    fecha_solicitud = models.DateTimeField(auto_now_add=True)
    fecha_aprobacion = models.DateTimeField(null=True, blank=True)
    fecha_reembolso = models.DateTimeField(null=True, blank=True)

    class Meta:
        """Meta definición del modelo."""
        ordering = ["-fecha_solicitud"]
        verbose_name = "Anulación"
        verbose_name_plural = "Anulaciones"

    def __str__(self):
        return f"Anulación {self.get_tipo_anulacion_display()} - {self.boleto}"

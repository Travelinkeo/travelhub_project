"""Módulo provider de la aplicación communications.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _

from core.api import AgenciaMixin


class ComunicacionProveedor(AgenciaMixin, models.Model):
    """
    Modelo para registrar las comunicaciones (emails, etc.) recibidas de proveedores.
    Permite el seguimiento de boletos, alertas y cambios de itinerario.
    """

    class Categoria(models.TextChoices):
        TICKET = "TICKET", _("Boleto / E-Ticket")
        RESERVATION = "RESERVATION", _("Reserva / PNR")
        ALERT = "ALERT", _("Alerta de Vuelo")
        CANCELLATION = "CANCELLATION", _("Cancelación")
        OTHER = "OTHER", _("Otro")

    remitente = models.CharField(max_length=255)
    asunto = models.CharField(max_length=500)
    fecha_recepcion = models.DateTimeField(auto_now_add=True, db_index=True)
    categoria = models.CharField(max_length=20, choices=Categoria.choices, default=Categoria.OTHER)

    # Datos extraídos por IA o Regex
    contenido_extraido = models.JSONField(default=dict, blank=True)
    cuerpo_completo = models.TextField(blank=True)

    # Metadata técnica
    message_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    procesado = models.BooleanField(default=False)

    class Meta:
        verbose_name = _("Comunicación de Proveedor")
        verbose_name_plural = _("Comunicaciones de Proveedores")
        ordering = ["-fecha_recepcion"]

    def __str__(self):
        # __str__: Representación en string del objeto. Returns: str.
        return f"{self.remitente} - {self.asunto[:50]}..."

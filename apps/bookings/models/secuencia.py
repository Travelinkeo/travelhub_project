from django.db import models
from django.utils.translation import gettext_lazy as _

from core.api import AgenciaMixin


class SecuenciaVentaDiaria(AgenciaMixin, models.Model):
    """
    Controla el contador diario de ventas por agencia de forma atómica en base de datos.
    Previene colisiones de localizadores (TOCTOU) bajo alta concurrencia.
    """

    id_secuencia = models.AutoField(primary_key=True)
    fecha = models.DateField(_("Fecha"), db_index=True)
    contador = models.PositiveIntegerField(_("Contador"), default=0)

    class Meta:
        verbose_name = _("Secuencia de Venta Diaria")
        verbose_name_plural = _("Secuencias de Ventas Diarias")
        unique_together = ("agencia", "fecha")
        db_table = "bookings_secuencia_venta_diaria"

    def __str__(self):
        """__str__."""
        return f"Secuencia {self.agencia_id} - {self.fecha}: {self.contador}"

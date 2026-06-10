from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.common.models import Moneda


class TipoCambio(models.Model):
    id_tipo_cambio = models.AutoField(primary_key=True, verbose_name=_("ID Tipo de Cambio"))
    moneda_origen = models.ForeignKey(
        Moneda,
        related_name="tipos_cambio_origen",
        on_delete=models.PROTECT,
        verbose_name=_("Moneda Origen"),
        null=True,
        blank=True,
    )
    moneda_destino = models.ForeignKey(
        Moneda,
        related_name="tipos_cambio_destino",
        on_delete=models.PROTECT,
        verbose_name=_("Moneda Destino"),
        null=True,
        blank=True,
    )
    fecha_efectiva = models.DateField(
        _("Fecha Efectiva"),
        default=timezone.now,
        help_text=_("Fecha en que esta tasa de cambio entra en vigor."),
    )
    tasa_conversion = models.DecimalField(
        _("Tasa de Conversión"),
        max_digits=18,
        decimal_places=8,
        help_text=_("Cuánto de la moneda destino equivale a 1 unidad de la moneda origen."),
    )

    class Meta:
        verbose_name = _("Tipo de Cambio")
        verbose_name_plural = _("Tipos de Cambio")
        ordering = ["-fecha_efectiva", "moneda_origen__codigo_iso"]
        unique_together = ("moneda_origen", "moneda_destino", "fecha_efectiva")

    def __str__(self):
        return f"{self.moneda_origen.codigo_iso} a {self.moneda_destino.codigo_iso} el {self.fecha_efectiva}: {self.tasa_conversion}"

    def clean(self):
        if self.moneda_origen == self.moneda_destino:
            raise ValidationError(_("La moneda de origen y destino no pueden ser la misma."))
        if self.tasa_conversion <= 0:
            raise ValidationError(_("La tasa de conversión debe ser un valor positivo."))


class TasaCambio(models.Model):
    """
    CACHÉ DE SUPERVIVENCIA FINANCIERA
    Almacena la tasa diaria del BCV.
    """

    fecha = models.DateField(db_index=True)
    moneda = models.CharField(
        max_length=3, default="USD", choices=[("USD", "Dólar"), ("EUR", "Euro")]
    )
    monto = models.DecimalField(max_digits=10, decimal_places=4, help_text="Tasa de cambio oficial")
    ultima_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("fecha", "moneda")
        ordering = ["-fecha"]
        verbose_name = "Tasa de Cambio"
        verbose_name_plural = "Tasas de Cambio"

    def __str__(self):
        return f"{self.moneda} - {self.monto} ({self.fecha})"


class TasaCambioBCV(models.Model):
    fecha = models.DateField(unique=True, db_index=True)
    tasa_usd = models.DecimalField(
        max_digits=10, decimal_places=4, help_text="Tasa de cambio oficial USD"
    )
    tasa_eur = models.DecimalField(
        max_digits=10, decimal_places=4, help_text="Tasa de cambio oficial EUR"
    )
    ultima_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fecha"]
        verbose_name = "Tasa de Cambio BCV"
        verbose_name_plural = "Tasas de Cambio BCV"

    def __str__(self):
        return f"BCV {self.fecha}: USD {self.tasa_usd}, EUR {self.tasa_eur}"

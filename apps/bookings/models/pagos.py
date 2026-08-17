from __future__ import annotations

from decimal import Decimal

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.common.models import Moneda
from core.api import AgenciaMixin, SoftDeleteModel


class FeeVenta(AgenciaMixin, SoftDeleteModel, models.Model):
    """FeeVenta."""

    id_fee_venta = models.AutoField(primary_key=True, verbose_name=_("ID Fee"))
    venta = models.ForeignKey(
        "bookings.Venta",
        related_name="fees_venta",
        on_delete=models.PROTECT,
        verbose_name=_("Venta"),
        null=True,
        blank=True,
    )

    class TipoFee(models.TextChoices):
        """TipoFee."""

        EMISION = "EMI", _("Emisión")
        CAMBIO = "CAM", _("Cambio / Exchange")
        GESTION = "GST", _("Gestión")
        URGENTE = "URG", _("Urgente")
        OTRO = "OTR", _("Otro")

    tipo_fee = models.CharField(
        _("Tipo Fee"), max_length=3, choices=TipoFee.choices, default=TipoFee.GESTION
    )
    descripcion = models.CharField(_("Descripción"), max_length=200, blank=True, null=True)
    monto = models.DecimalField(_("Monto"), max_digits=12, decimal_places=2)
    moneda = models.ForeignKey(
        Moneda, on_delete=models.PROTECT, verbose_name=_("Moneda"), null=True, blank=True
    )
    es_comision_agencia = models.BooleanField(_("Es Comisión Agencia"), default=True)
    taxable = models.BooleanField(_("Sujeto a Impuestos"), default=False)
    creado = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = _("Fee de Venta")
        verbose_name_plural = _("Fees de Venta")
        ordering = ["-creado"]

    def __str__(self):
        """__str__."""
        return f"{self.get_tipo_fee_display()} {self.monto} {self.moneda.codigo_iso if self.moneda else ''}"


class PagoVenta(AgenciaMixin, models.Model):
    """PagoVenta."""

    id_pago_venta = models.AutoField(primary_key=True, verbose_name=_("ID Pago"))
    venta = models.ForeignKey(
        "bookings.Venta",
        related_name="pagos_venta",
        on_delete=models.PROTECT,
        verbose_name=_("Venta"),
        null=True,
        blank=True,
    )
    fecha_pago = models.DateTimeField(_("Fecha Pago"), default=timezone.now)
    monto = models.DecimalField(_("Monto"), max_digits=12, decimal_places=2)
    moneda = models.ForeignKey(
        Moneda, on_delete=models.PROTECT, verbose_name=_("Moneda"), null=True, blank=True
    )

    class MetodoPago(models.TextChoices):
        """MetodoPago."""

        EFECTIVO = "EFE", _("Efectivo")
        TARJETA = "TAR", _("Tarjeta")
        TRANSFERENCIA = "TRF", _("Transferencia")
        ZELLE = "ZEL", _("Zelle")
        PAYPAL = "PPL", _("PayPal")
        SALDO_A_FAVOR = "SAF", _("Saldo a Favor / Billetera")
        OTRO = "OTR", _("Otro")

    metodo = models.CharField(
        _("Método"), max_length=3, choices=MetodoPago.choices, default=MetodoPago.TRANSFERENCIA
    )
    referencia = models.CharField(_("Referencia"), max_length=100, blank=True, null=True)
    confirmado = models.BooleanField(_("Confirmado"), default=True)

    aplica_igtf = models.BooleanField(_("Aplica IGTF (3%)"), default=False)
    tasa_igtf = models.DecimalField(_("Tasa IGTF %"), max_digits=5, decimal_places=2, default=3.00)
    monto_igtf = models.DecimalField(_("Monto IGTF"), max_digits=12, decimal_places=2, default=0)

    notas = models.TextField(_("Notas"), blank=True, null=True)
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Pago de Venta")
        verbose_name_plural = _("Pagos de Venta")
        ordering = ["-fecha_pago"]
        indexes = [
            models.Index(fields=["agencia", "venta"], name="idx_pago_agencia_venta"),
            models.Index(fields=["agencia", "fecha_pago"], name="idx_pago_agencia_fecha"),
            models.Index(fields=["metodo"], name="idx_pago_metodo"),
            models.Index(fields=["creado"], name="idx_pagoventa_creado"),
        ]

    def __str__(self):
        """__str__."""
        return f"Pago {self.monto} {self.moneda.codigo_iso if self.moneda else ''}"

    def save(self, *args, **kwargs):
        """save."""
        if self.aplica_igtf and self.monto:
            self.monto_igtf = (self.monto * (self.tasa_igtf / Decimal("100"))).quantize(
                Decimal("0.01")
            )
        else:
            self.monto_igtf = Decimal("0.00")
        super().save(*args, **kwargs)

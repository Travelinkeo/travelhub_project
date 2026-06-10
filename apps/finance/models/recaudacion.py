from decimal import Decimal

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from core.api import AgenciaMixin, SoftDeleteModel

from .currencies import Moneda


class CanalRecaudacion(AgenciaMixin, SoftDeleteModel, models.Model):
    class TipoCanal(models.TextChoices):
        CONSOLIDADOR = "CONSOLIDADOR", _("Consolidador Internacional (IATA/BSP)")
        EFECTIVO = "EFECTIVO", _("Efectivo Cash USD")
        CUSTODIA = "CUSTODIA", _("Cuenta de Custodia Nacional")

    nombre = models.CharField(_("Nombre del Canal"), max_length=100)
    tipo = models.CharField(_("Tipo de Canal"), max_length=20, choices=TipoCanal.choices)
    moneda = models.ForeignKey(Moneda, on_delete=models.PROTECT, verbose_name=_("Moneda"))
    descripcion = models.TextField(_("Descripción / Detalles Cuenta"), blank=True, null=True)
    activo = models.BooleanField(_("Activo"), default=True)
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Canal de Recaudación")
        verbose_name_plural = _("Canales de Recaudación")
        ordering = ["nombre"]

    def __str__(self):
        return f"{self.nombre} ({self.get_tipo_display()})"


class Pago(AgenciaMixin, SoftDeleteModel, models.Model):
    id_pago = models.AutoField(primary_key=True)
    venta = models.ForeignKey(
        "bookings.Venta",
        on_delete=models.CASCADE,
        related_name="pagos_finanzas_recaudacion",
        verbose_name=_("Venta"),
    )
    canal_recaudacion = models.ForeignKey(
        CanalRecaudacion,
        on_delete=models.PROTECT,
        related_name="pagos",
        verbose_name=_("Canal de Recaudación"),
    )
    monto = models.DecimalField(_("Monto Pago"), max_digits=12, decimal_places=2)
    moneda = models.ForeignKey(Moneda, on_delete=models.PROTECT, verbose_name=_("Moneda"))
    tasa_cambio = models.DecimalField(
        _("Tasa de Cambio"), max_digits=12, decimal_places=4, default=Decimal("1.0000")
    )
    igtf_monto = models.DecimalField(
        _("Monto IGTF (3%)"), max_digits=12, decimal_places=2, default=Decimal("0.00")
    )
    igtf_aplicado = models.BooleanField(_("IGTF Aplicado"), default=False)
    referencia = models.CharField(
        _("Referencia de Transacción"), max_length=100, blank=True, null=True
    )
    fecha_pago = models.DateField(_("Fecha de Pago"), default=timezone.now)
    confirmado = models.BooleanField(_("Confirmado"), default=True)
    comprobante = models.FileField(
        _("Comprobante de Pago"),
        upload_to="recaudaciones/comprobantes/%Y/%m/",
        blank=True,
        null=True,
    )
    notas = models.TextField(_("Notas"), blank=True, null=True)
    creado = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = _("Pago de Recaudación")
        verbose_name_plural = _("Pagos de Recaudación")
        ordering = ["-fecha_pago", "-creado"]

    def __str__(self):
        return f"Pago {self.monto} {self.moneda.codigo_iso if self.moneda else ''} - Venta {self.venta.localizador if self.venta else self.id_pago}"

    def save(self, *args, **kwargs):
        # 1. Verificar si la agencia es contribuyente especial de forma segura
        is_contribuyente_especial = False
        if self.agencia:
            is_contribuyente_especial = getattr(self.agencia, "es_contribuyente_especial", False)
            if not is_contribuyente_especial and hasattr(self.agencia, "configuracion"):
                config = self.agencia.configuracion
                is_contribuyente_especial = getattr(
                    config, "es_sujeto_pasivo_especial", False
                ) or getattr(config, "es_contribuyente_especial", False)

        # 2. IGTF (3%) aplica si es contribuyente especial, se paga en divisas (moneda no VES)
        # y el canal es efectivo o custodia.
        if is_contribuyente_especial and self.moneda and self.moneda.codigo_iso != "VES":
            if self.canal_recaudacion and self.canal_recaudacion.tipo in [
                CanalRecaudacion.TipoCanal.EFECTIVO,
                CanalRecaudacion.TipoCanal.CUSTODIA,
            ]:
                self.igtf_aplicado = True
                self.igtf_monto = (self.monto * Decimal("0.03")).quantize(Decimal("0.01"))
            else:
                self.igtf_aplicado = False
                self.igtf_monto = Decimal("0.00")
        else:
            self.igtf_aplicado = False
            self.igtf_monto = Decimal("0.00")

        super().save(*args, **kwargs)

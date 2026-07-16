import datetime

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models

from core.models.base import AgenciaMixin


# Stub for migration compatibility — will be removed after squashing
class DetalleAsiento(models.Model):
    class Meta:
        managed = False


class PlanContable(models.Model):
    class Meta:
        managed = False


class ItemLiquidacion(models.Model):
    class Meta:
        managed = False


class LiquidacionProveedor(models.Model):
    class Meta:
        managed = False


class CuentaContable(AgenciaMixin, models.Model):
    codigo = models.CharField(max_length=30)
    nombre = models.CharField(max_length=100)

    class TipoCuenta(models.TextChoices):
        ACTIVO = "ACTIVO", "Activo"
        PASIVO = "PASIVO", "Pasivo"
        PATRIMONIO = "PATRIMONIO", "Patrimonio"
        INGRESO = "INGRESO", "Ingreso"
        GASTO = "GASTO", "Gasto"

    tipo = models.CharField(max_length=10, choices=TipoCuenta.choices)
    cuenta_padre = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="subcuentas",
    )
    acepta_movimientos = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Cuenta Contable"
        verbose_name_plural = "Cuentas Contables"
        ordering = ["codigo"]
        unique_together = [("agencia", "codigo")]

    def __str__(self):
        return f"{self.codigo} — {self.nombre}"


class AsientoContable(AgenciaMixin, models.Model):
    fecha_contable = models.DateField(default=datetime.date.today)
    glosa = models.CharField(max_length=255, blank=True, default="")

    content_type = models.ForeignKey(ContentType, on_delete=models.PROTECT, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey("content_type", "object_id")

    class EstadoAsiento(models.TextChoices):
        BORRADOR = "BORRADOR", "Borrador"
        CONTABILIZADO = "CONTABILIZADO", "Contabilizado"
        ANULADO = "ANULADO", "Anulado"

    class TipoAsiento(models.TextChoices):
        DIARIO = "DIARIO", "Diario"
        VENTAS = "VENTAS", "Ventas"
        AJUSTE = "AJUSTE", "Ajuste"
        CIERRE = "CIERRE", "Cierre"

    estado = models.CharField(
        max_length=20, choices=EstadoAsiento.choices, default=EstadoAsiento.BORRADOR
    )
    tipo_asiento = models.CharField(
        max_length=7, choices=TipoAsiento.choices, default=TipoAsiento.DIARIO
    )

    class Meta:
        verbose_name = "Asiento Contable"
        verbose_name_plural = "Asientos Contables"
        ordering = ["-fecha_contable"]
        indexes = [
            models.Index(fields=["content_type", "object_id"]),
        ]

    def __str__(self):
        return f"Asiento #{self.pk} — {self.glosa[:60]}"


class MovimientoContable(AgenciaMixin, models.Model):
    asiento = models.ForeignKey(
        AsientoContable,
        on_delete=models.CASCADE,
        related_name="movimientos",
    )
    cuenta = models.ForeignKey(
        CuentaContable,
        on_delete=models.PROTECT,
        limit_choices_to={"acepta_movimientos": True},
    )

    class TipoMovimiento(models.TextChoices):
        DEBITO = "DEBITO", "Débito"
        CREDITO = "CREDITO", "Crédito"

    tipo = models.CharField(max_length=7, choices=TipoMovimiento.choices)
    monto_ves = models.DecimalField(max_digits=15, decimal_places=4)
    monto_usd = models.DecimalField(max_digits=15, decimal_places=4)

    class Meta:
        verbose_name = "Movimiento Contable"
        verbose_name_plural = "Movimientos Contables"
        ordering = ["asiento", "pk"]

    def __str__(self):
        return f"{self.tipo} — VES {self.monto_ves} / USD {self.monto_usd} | {self.cuenta.nombre}"

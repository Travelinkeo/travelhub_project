"""Modelos de base de datos para la aplicación contabilidad.
"""

import datetime

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models

from core.models.base import AgenciaMixin


# Stub for migration compatibility — will be removed after squashing
class DetalleAsiento:
    """Clase DetalleAsiento. Uso: según contexto de la aplicación.
    """
    class Meta:
        managed = False


class PlanContable:
    """Clase PlanContable. Uso: según contexto de la aplicación.
    """
    class Meta:
        managed = False


class ItemLiquidacion:
    """Clase ItemLiquidacion. Uso: según contexto de la aplicación.
    """
    class Meta:
        managed = False


class LiquidacionProveedor:
    """Clase LiquidacionProveedor. Uso: según contexto de la aplicación.
    """
    class Meta:
        managed = False


class CuentaContable:
    """Clase CuentaContable. Uso: según contexto de la aplicación.
    """
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
        # __str__: Representación en string del objeto. Returns: str.
        return f"{self.codigo} — {self.nombre}"


class AsientoContable:
    """Clase AsientoContable. Uso: según contexto de la aplicación.
    """
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
        # __str__: Representación en string del objeto. Returns: str.
        return f"Asiento #{self.pk} — {self.glosa[:60]}"


class MovimientoContable:
    """Clase MovimientoContable. Uso: según contexto de la aplicación.
    """
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
        # __str__: Representación en string del objeto. Returns: str.
        return f"{self.tipo} — VES {self.monto_ves} / USD {self.monto_usd} | {self.cuenta.nombre}"


class ReporteVentaProveedor(AgenciaMixin, models.Model):
    """
    Encabezado de Reporte de Ventas Semanal/Mensual enviado por Proveedores (CTG, MY DESTINY, etc.).
    Multi-tenant por AgenciaMixin.
    """

    class EstadoReporte(models.TextChoices):
        PROCESADO = "PROCESADO", "Procesado"
        CONCILIADO = "CONCILIADO", "Conciliado"
        DIFERENCIA = "DIFERENCIA", "Con Diferencias"
        ERROR = "ERROR", "Error"

    proveedor_nombre = models.CharField(max_length=100, db_index=True)
    codigo_agencia_proveedor = models.CharField(max_length=50, blank=True, default="")
    asunto_correo = models.CharField(max_length=255, blank=True, default="")
    emisor_correo = models.CharField(max_length=150, blank=True, default="")
    fecha_reporte_desde = models.DateField(null=True, blank=True)
    fecha_reporte_hasta = models.DateField(null=True, blank=True)
    fecha_procesamiento = models.DateTimeField(auto_now_add=True)
    nombre_archivo_adjunto = models.CharField(max_length=255, blank=True, default="")

    saldo_anterior = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    monto_total_ventas = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    saldo_final = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    estado = models.CharField(
        max_length=25, choices=EstadoReporte.choices, default=EstadoReporte.PROCESADO
    )
    raw_data = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = "Reporte de Venta de Proveedor"
        verbose_name_plural = "Reportes de Ventas de Proveedores"
        ordering = ["-fecha_procesamiento"]

    def __str__(self):
        # __str__: Representación en string del objeto. Returns: str.
        return f"Reporte {self.proveedor_nombre} [{self.fecha_reporte_desde} a {self.fecha_reporte_hasta}] — {self.agencia.nombre if self.agencia else 'Global'}"


class ItemReporteVentaProveedor(AgenciaMixin, models.Model):
    """
    Línea de Boleto/Servicio dentro de un Reporte de Venta de Proveedor.
    Multi-tenant por AgenciaMixin.
    """

    reporte = models.ForeignKey(
        ReporteVentaProveedor,
        on_delete=models.CASCADE,
        related_name="items",
    )
    fecha_emision = models.DateField(null=True, blank=True)
    numero_factura = models.CharField(max_length=50, blank=True, default="")
    numero_boleto = models.CharField(max_length=50, db_index=True)
    pasajero = models.CharField(max_length=150, blank=True, default="")
    aerolinea = models.CharField(max_length=100, blank=True, default="")
    fecha_vuelo = models.DateField(null=True, blank=True)
    ruta_itinerario = models.CharField(max_length=100, blank=True, default="")

    monto_fare = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    monto_tax = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    monto_subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    monto_fee = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    porcentaje_comision = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    monto_comision = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    monto_neto_pagar = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    remarks = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        verbose_name = "Item de Reporte de Proveedor"
        verbose_name_plural = "Items de Reportes de Proveedores"
        ordering = ["reporte", "pk"]

    def __str__(self):
        # __str__: Representación en string del objeto. Returns: str.
        return f"Boleto #{self.numero_boleto} ({self.pasajero}) — {self.aerolinea} (${self.monto_neto_pagar})"

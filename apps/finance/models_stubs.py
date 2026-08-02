import uuid
from datetime import timedelta
from decimal import Decimal

import django.utils.timezone
from django.db import models

from core.models.base import AgenciaMixinStubs


class StubQuerySet(models.QuerySet):
    """StubQuerySet."""

    def hard_delete(self):
        """hard_delete."""
        return super().delete()

    def restore(self):
        """restore."""
        self.update(is_deleted=False, deleted_at=None)


class StubManager(models.Manager):
    """StubManager."""

    def get_queryset(self):
        """get_queryset."""
        return StubQuerySet(self.model, using=self._db)


class CanalRecaudacion(AgenciaMixinStubs):
    """CanalRecaudacion."""

    class TipoCanal(models.TextChoices):
        """TipoCanal."""

        EFECTIVO = "EFE", "Efectivo"
        CONSOLIDADOR = "CON", "Consolidador"
        CUSTODIA = "CUS", "Custodia"

    id_canal = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100)
    tipo = models.CharField(max_length=3, choices=TipoCanal.choices)
    descripcion = models.TextField(blank=True)
    activo = models.BooleanField(default=True)
    moneda = models.ForeignKey("common.Moneda", models.DO_NOTHING, blank=True, null=True)

    class Meta:
        managed = False
        db_table = "finance_canalrecaudacion"


class ComisionVenta(AgenciaMixinStubs):
    """ComisionVenta."""

    class EstadoComision(models.TextChoices):
        """EstadoComision."""

        PENDIENTE = "PEN", "Pendiente"
        LIQUIDADO = "LIQ", "Liquidado"

    id = models.BigAutoField(primary_key=True)
    is_deleted = models.BooleanField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    monto_base_calculo = models.DecimalField(max_digits=12, decimal_places=2)
    monto_comision = models.DecimalField(max_digits=12, decimal_places=2)
    estado = models.CharField(max_length=3, choices=EstadoComision.choices)
    fecha_calculo = models.DateTimeField()
    fecha_liquidacion = models.DateTimeField(blank=True, null=True)
    venta_id = models.IntegerField()
    agente = models.ForeignKey("auth.User", models.DO_NOTHING)
    liquidacion_asociada = models.ForeignKey(
        "finance.LiquidacionAgente", models.DO_NOTHING, blank=True, null=True
    )
    regla_aplicada = models.ForeignKey(
        "finance.ReglaComision", models.DO_NOTHING, blank=True, null=True
    )

    class Meta:
        managed = False
        db_table = "finance_comisionventa"


class ConciliacionBoleto(AgenciaMixinStubs):
    """ConciliacionBoleto."""

    class EstadosCruce(models.TextChoices):
        """EstadosCruce."""

        OK = "OK", "Ok"
        DISCREPANCIA = "DIS", "Discrepancia"
        NO_EN_LOCAL = "NOL", "No en local"
        NO_EN_REPORTE = "NOR", "No en reporte"

    objects = StubManager()
    all_objects = StubManager()
    id_conciliacion = models.AutoField(primary_key=True)
    estado = models.CharField(max_length=20, choices=EstadosCruce.choices)
    diferencia_tarifa = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0.00")
    )
    diferencia_impuestos = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0.00")
    )
    diferencia_total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    ia_razonamiento = models.TextField(blank=True, null=True)
    resolucion_notas = models.TextField(blank=True, null=True)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(blank=True, null=True)
    boleto_local = models.OneToOneField(
        "bookings.BoletoImportado", models.DO_NOTHING, blank=True, null=True
    )
    sugerencia_asiento_id = models.IntegerField(blank=True, null=True)
    linea_reporte = models.OneToOneField(
        "finance.LineaReporteReconciliacion", models.DO_NOTHING, blank=True, null=True
    )
    reporte = models.ForeignKey(
        "finance.ReporteReconciliacion", models.DO_NOTHING, related_name="conciliaciones"
    )

    def __str__(self):
        """__str__."""
        return f"{self.estado} - ${self.diferencia_total}"

    class Meta:
        managed = False
        db_table = "finance_conciliacionboleto"


class DiferenciaFinanciera(AgenciaMixinStubs):
    """DiferenciaFinanciera."""

    id = models.BigAutoField(primary_key=True)
    campo_discrepancia = models.CharField(max_length=50)
    valor_sistema = models.DecimalField(max_digits=12, decimal_places=2)
    valor_proveedor = models.DecimalField(max_digits=12, decimal_places=2)
    diferencia = models.DecimalField(max_digits=12, decimal_places=2)
    resuelto = models.BooleanField()
    fecha_resolucion = models.DateTimeField(blank=True, null=True)
    item_reporte = models.ForeignKey("finance.ItemReporte", models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = "finance_diferenciafinanciera"


class DocumentoExportacion(AgenciaMixinStubs):
    """DocumentoExportacion."""

    class Meta:
        managed = False
        db_table = "finance_documentoexportacion"


class DocumentoExportacionConsolidado(AgenciaMixinStubs):
    """DocumentoExportacionConsolidado."""

    id = models.BigAutoField(primary_key=True)
    tipo_documento = models.CharField(max_length=20, default="")
    numero_documento = models.CharField(max_length=100, default="")
    archivo = models.CharField(max_length=100, default="")
    fecha_subida = models.DateTimeField(default=django.utils.timezone.now)
    factura = models.ForeignKey(
        "finance.FacturaConsolidada", models.DO_NOTHING, blank=True, null=True
    )

    class Meta:
        managed = False
        db_table = "finance_documentoexportacionconsolidado"


# FacturaConsolidada e ItemFacturaConsolidada fueron migrados a models.py (managed=True).
# Re-exportados aquí para backwards-compatibility con módulos que importan desde models_stubs.
from apps.finance.models import FacturaConsolidada, ItemFacturaConsolidada  # noqa: F401, E402


class FacturaFiscal(AgenciaMixinStubs):
    """FacturaFiscal."""

    class EstadoFiscal(models.TextChoices):
        """EstadoFiscal."""

        PENDIENTE = "PEN", "Pendiente"
        EN_PROCESO = "PRO", "En Proceso"
        APROBADA = "APR", "Aprobada"
        RECHAZADA = "REC", "Rechazada"

    class Meta:
        managed = False
        db_table = "finance_facturafiscal"


class FacturaProveedor(AgenciaMixinStubs):
    """FacturaProveedor."""

    class EstadoFactura(models.TextChoices):
        """EstadoFactura."""

        CONCILIADA = "CON", "Conciliada"
        REQUIERE_REVISION = "REV", "Requiere Revision"

    class Meta:
        managed = False
        db_table = "finance_facturaproveedor"


# GastoOperativo fue migrado a models.py (managed=True).
# Re-exportado aquí para backwards-compatibility.
from apps.finance.models import GastoOperativo  # noqa: F401, E402


class ItemReporte(AgenciaMixinStubs):
    """ItemReporte."""

    class EstadoConciliacion(models.TextChoices):
        """EstadoConciliacion."""

        MATCH = "MAT", "Match"
        MISSING_INTERNAL = "MIS", "Missing Internal"

    id = models.BigAutoField(primary_key=True)
    numero_boleto = models.CharField(max_length=50)
    pnr = models.CharField(max_length=10, blank=True, null=True)
    pasajero = models.CharField(max_length=200, blank=True, null=True)
    fecha_emision = models.DateField(blank=True, null=True)
    monto_total_proveedor = models.DecimalField(max_digits=12, decimal_places=2)
    monto_sistema = models.DecimalField(max_digits=12, decimal_places=2)
    tax_proveedor = models.DecimalField(max_digits=12, decimal_places=2)
    comision_proveedor = models.DecimalField(max_digits=12, decimal_places=2)
    estado = models.CharField(max_length=3, choices=EstadoConciliacion.choices)
    fecha_conciliacion = models.DateTimeField(blank=True, null=True)
    boleto_interno = models.ForeignKey(
        "bookings.BoletoImportado", models.DO_NOTHING, blank=True, null=True
    )
    reporte = models.ForeignKey("finance.ReporteProveedor", models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = "finance_itemreporte"


class LineaReporteReconciliacion(AgenciaMixinStubs):
    """LineaReporteReconciliacion."""

    id_linea = models.AutoField(primary_key=True)
    numero_boleto_reportado = models.CharField(max_length=150)
    tarifa_base_cobrada = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0.00")
    )
    impuestos_cobrados = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0.00")
    )
    comision_cedida = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    total_cobrado = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    raw_data = models.JSONField(blank=True, null=True)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(blank=True, null=True)
    reporte = models.ForeignKey("finance.ReporteReconciliacion", models.DO_NOTHING)

    def __str__(self):
        """__str__."""
        return f"{self.numero_boleto_reportado} - ${self.total_cobrado}"

    class Meta:
        managed = False
        db_table = "finance_lineareportereconciliacion"


class LinkDePago(AgenciaMixinStubs):
    """LinkDePago."""

    class EstadoPago(models.TextChoices):
        """EstadoPago."""

        PENDIENTE = "PEN", "Pendiente"
        PAGADO = "PAG", "Pagado"
        EN_REVISION = "REV", "En Revision"

    objects = models.Manager()
    all_objects = models.Manager()

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    monto_total = models.DecimalField(max_digits=12, decimal_places=2)
    moneda = models.CharField(max_length=3, default="USD")
    estado = models.CharField(
        max_length=3, choices=EstadoPago.choices, default=EstadoPago.PENDIENTE
    )
    referencia_pago = models.CharField(max_length=100, blank=True, null=True)
    comprobante_imagen = models.CharField(max_length=100, blank=True, null=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    expira_en = models.DateTimeField()
    venta = models.ForeignKey("bookings.Venta", models.DO_NOTHING)

    def save(self, *args, **kwargs):
        """save."""
        if not self.expira_en:
            self.expira_en = django.utils.timezone.now() + timedelta(hours=24)
        super().save(*args, **kwargs)

    @property
    def esta_activo(self):
        return (
            self.estado == self.EstadoPago.PENDIENTE
            and self.expira_en > django.utils.timezone.now()
        )

    class Meta:
        managed = False
        db_table = "finance_linkdepago"


class LiquidacionAgente(AgenciaMixinStubs):
    """LiquidacionAgente."""

    id = models.BigAutoField(primary_key=True)
    is_deleted = models.BooleanField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    periodo_mes = models.IntegerField()
    periodo_anio = models.IntegerField()
    total_comisiones = models.DecimalField(max_digits=12, decimal_places=2)
    cantidad_ventas = models.IntegerField()
    fecha_generacion = models.DateTimeField()
    pagado = models.BooleanField()
    referencia_pago = models.CharField(max_length=100)
    agente = models.ForeignKey("auth.User", models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = "finance_liquidacionagente"
        unique_together = (("agente", "periodo_mes", "periodo_anio"),)


class Moneda(AgenciaMixinStubs):
    """Moneda."""

    codigo_iso = models.CharField(max_length=3)
    nombre = models.CharField(max_length=50)
    simbolo = models.CharField(max_length=5)

    class Meta:
        managed = False
        db_table = "finance_moneda"


class PagoBinance(AgenciaMixinStubs):
    """PagoBinance."""

    id_pago_binance = models.AutoField(primary_key=True)
    prepay_id = models.CharField(max_length=100, blank=True, null=True)
    merchant_trade_no = models.CharField(unique=True, max_length=50)
    checkout_url = models.CharField(max_length=500, blank=True, null=True)
    monto = models.DecimalField(max_digits=12, decimal_places=2)
    moneda = models.CharField(max_length=5)
    estado = models.CharField(max_length=3)
    fecha_creacion = models.DateTimeField()
    fecha_actualizacion = models.DateTimeField()
    raw_response = models.JSONField()
    factura_id = models.IntegerField()
    is_deleted = models.BooleanField()
    deleted_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "finance_pagobinance"


class PropuestaTransaccionIA(AgenciaMixinStubs):
    """PropuestaTransaccionIA."""

    class EstadoPropuesta(models.TextChoices):
        """EstadoPropuesta."""

        PENDIENTE = "PEN", "Pendiente"
        RECHAZADA = "REC", "Rechazada"
        APROBADA = "APR", "Aprobada"

    class Meta:
        managed = False
        db_table = "finance_propuestatransaccionia"


class ReglaComision(AgenciaMixinStubs):
    """ReglaComision."""

    class TipoCalculo(models.TextChoices):
        """TipoCalculo."""

        PORCENTAJE_UTILIDAD = "UTI", "% Utilidad"
        PORCENTAJE_VENTA = "VEN", "% Venta"
        MONTO_FIJO = "FIJ", "Monto Fijo"

    id = models.BigAutoField(primary_key=True)
    is_deleted = models.BooleanField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    tipo_calculo = models.CharField(max_length=5, choices=TipoCalculo.choices)
    valor = models.DecimalField(max_digits=12, decimal_places=2)
    activo = models.BooleanField()
    fecha_creacion = models.DateTimeField()
    agente = models.ForeignKey("auth.User", models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = "finance_reglacomision"
        unique_together = (("agencia", "agente"),)


class ReporteProveedor(AgenciaMixinStubs):
    """ReporteProveedor."""

    class EstadoReporte(models.TextChoices):
        """EstadoReporte."""

        PENDIENTE = "PEN", "Pendiente"

    id = models.BigAutoField(primary_key=True)
    archivo = models.CharField(max_length=100)
    fecha_carga = models.DateTimeField()
    estado = models.CharField(max_length=3, choices=EstadoReporte.choices)
    total_registros = models.IntegerField()
    total_con_diferencia = models.IntegerField()
    notas = models.TextField()
    proveedor = models.ForeignKey("bookings.Proveedor", models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = "finance_reporteproveedor"


class ReporteReconciliacion(AgenciaMixinStubs):
    """ReporteReconciliacion."""

    class Estados(models.TextChoices):
        """Estados."""

        PROCESADO = "PRO", "Procesado"
        PENDIENTE = "PEN", "Pendiente"
        PROCESANDO = "PRC", "Procesando"
        CON_DISCREPANCIAS = "DIS", "Con Discrepancias"
        CONCILIADO = "CON", "Conciliado"
        ERROR = "ERR", "Error"

    id_reporte = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    archivo = models.CharField(max_length=100, default="")
    fecha_subida = models.DateTimeField(default=django.utils.timezone.now)
    proveedor = models.CharField(max_length=50)
    periodo_inicio = models.DateField(blank=True, null=True)
    periodo_fin = models.DateField(blank=True, null=True)
    estado = models.CharField(max_length=20, choices=Estados.choices)
    datos_extraidos = models.JSONField(blank=True, null=True)
    resumen_conciliacion = models.JSONField(blank=True, null=True)
    error_log = models.TextField(blank=True, null=True)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(blank=True, null=True)
    agencia = models.ForeignKey("core.Agencia", models.DO_NOTHING, blank=True, null=True)

    @property
    def discrepancias_count(self):
        return self.conciliaciones.filter(
            estado=ConciliacionBoleto.EstadosCruce.DISCREPANCIA
        ).count()

    def __str__(self):
        """__str__."""
        agencia_nombre = self.agencia.nombre if self.agencia else "N/A"
        return f"Reporte {self.proveedor} - {self.fecha_subida.strftime('%d/%m/%Y')} ({agencia_nombre})"

    class Meta:
        managed = False
        db_table = "finance_reportereconciliacion"


# RetencionISLR fue migrado a models.py (managed=True).
# Re-exportado aquí para backwards-compatibility.
from apps.finance.models import RetencionISLR  # noqa: F401, E402


class TasaCambio(models.Model):
    """TasaCambio.

    NOTA: NO hereda de AgenciaMixinStubs porque la tabla real
    ``finance_tasacambio`` no tiene la columna ``agencia_id``.
    """

    id = models.BigAutoField(primary_key=True)
    fecha = models.DateField()
    moneda = models.CharField(max_length=3)
    monto = models.DecimalField(max_digits=10, decimal_places=4)
    ultima_actualizacion = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "finance_tasacambio"
        unique_together = (("fecha", "moneda"),)


class TaxRefundOpportunity(AgenciaMixinStubs):
    """TaxRefundOpportunity."""

    class Estado(models.TextChoices):
        """Estado."""

        ELEGIBLE = "ELE", "Elegible"
        TRAMITANDO = "TRA", "Tramitando"
        COMPLETADO = "COM", "Completado"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    monto_estimado = models.DecimalField(max_digits=10, decimal_places=2)
    monto_recuperado = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    estado = models.CharField(max_length=3, choices=Estado.choices, default=Estado.ELEGIBLE)
    tracking_code_proveedor = models.CharField(max_length=100, blank=True, null=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)
    boleto = models.OneToOneField("bookings.BoletoImportado", models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = "finance_taxrefundopportunity"


class TipoCambio(models.Model):
    """TipoCambio.

    NOTA: NO hereda de AgenciaMixinStubs porque la tabla real
    ``finance_tipocambio`` no tiene la columna ``agencia_id``.
    """

    id_tipo_cambio = models.AutoField(primary_key=True)
    fecha_efectiva = models.DateField()
    tasa_conversion = models.DecimalField(max_digits=18, decimal_places=8)
    moneda_destino = models.ForeignKey("common.Moneda", models.DO_NOTHING, blank=True, null=True)
    moneda_origen = models.ForeignKey(
        "common.Moneda",
        models.DO_NOTHING,
        related_name="financetipocambio_moneda_origen_set",
        blank=True,
        null=True,
    )

    class Meta:
        managed = False
        db_table = "finance_tipocambio"
        unique_together = (("moneda_origen", "moneda_destino", "fecha_efectiva"),)


class TransaccionPago(AgenciaMixinStubs):
    """TransaccionPago."""

    id_transaccion = models.AutoField(primary_key=True)
    proveedor = models.CharField(max_length=3)
    monto = models.DecimalField(max_digits=12, decimal_places=2)
    moneda = models.CharField(max_length=10)
    webhook_transaction_id = models.CharField(unique=True, max_length=255)
    data_raw = models.JSONField()
    fecha_registro = models.DateTimeField()
    is_deleted = models.BooleanField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    venta = models.ForeignKey("bookings.Venta", models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = "finance_transaccionpago"

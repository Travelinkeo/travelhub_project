import uuid
from datetime import date
from decimal import Decimal

import django.utils.timezone
from django.core.exceptions import ValidationError
from django.db import models


class StubQuerySet(models.QuerySet):
    def hard_delete(self):
        return super().delete()

    def restore(self):
        self.update(is_deleted=False, deleted_at=None)


class StubManager(models.Manager):
    def get_queryset(self):
        return StubQuerySet(self.model, using=self._db)


class CanalRecaudacion(models.Model):
    class TipoCanal(models.TextChoices):
        EFECTIVO = "EFE", "Efectivo"
        CONSOLIDADOR = "CON", "Consolidador"
        CUSTODIA = "CUS", "Custodia"

    id_canal = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100)
    tipo = models.CharField(max_length=3, choices=TipoCanal.choices)
    descripcion = models.TextField(blank=True)
    activo = models.BooleanField(default=True)
    moneda = models.ForeignKey("common.Moneda", models.DO_NOTHING, blank=True, null=True)
    agencia = models.ForeignKey("core.Agencia", models.DO_NOTHING, blank=True, null=True)

    class Meta:
        managed = False
        db_table = "finance_canalrecaudacion"


class ComisionVenta(models.Model):
    class EstadoComision(models.TextChoices):
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
    agencia = models.ForeignKey("core.Agencia", models.DO_NOTHING, blank=True, null=True)
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


class ConciliacionBoleto(models.Model):
    class EstadosCruce(models.TextChoices):
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
    agencia = models.ForeignKey("core.Agencia", models.DO_NOTHING, blank=True, null=True)

    def __str__(self):
        return f"{self.estado} - ${self.diferencia_total}"

    class Meta:
        managed = False
        db_table = "finance_conciliacionboleto"


class DiferenciaFinanciera(models.Model):
    id = models.BigAutoField(primary_key=True)
    campo_discrepancia = models.CharField(max_length=50)
    valor_sistema = models.DecimalField(max_digits=12, decimal_places=2)
    valor_proveedor = models.DecimalField(max_digits=12, decimal_places=2)
    diferencia = models.DecimalField(max_digits=12, decimal_places=2)
    resuelto = models.BooleanField()
    fecha_resolucion = models.DateTimeField(blank=True, null=True)
    item_reporte = models.ForeignKey("finance.ItemReporte", models.DO_NOTHING)
    agencia = models.ForeignKey("core.Agencia", models.DO_NOTHING, blank=True, null=True)

    class Meta:
        managed = False
        db_table = "finance_diferenciafinanciera"


class DocumentoExportacion(models.Model):
    class Meta:
        managed = False
        db_table = "finance_documentoexportacion"


class DocumentoExportacionConsolidado(models.Model):
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


class FacturaConsolidada(models.Model):
    class TipoOperacion(models.TextChoices):
        VENTA_PROPIA = "VP", "Venta Propia"
        INTERMEDIACION = "IN", "Intermediacion"

    class MonedaOperacion(models.TextChoices):
        DIVISA = "DIV", "Divisa"
        BOLIVAR = "BS", "Bolivar"

    class EstadoFactura(models.TextChoices):
        EMITIDA = "EMI", "Emitida"
        BORRADOR = "BOR", "Borrador"
        PAGADA = "PAG", "Pagada"
        PARCIAL = "PAR", "Parcial"
        VENCIDA = "VEN", "Vencida"
        ANULADA = "ANU", "Anulada"

    id_factura = models.AutoField(primary_key=True)
    numero_factura = models.CharField(unique=True, max_length=50, default="")
    numero_control = models.CharField(max_length=50, default="")
    fecha_emision = models.DateField(default=date.today)
    fecha_vencimiento = models.DateField(blank=True, null=True)
    emisor_rif = models.CharField(max_length=20, default="")
    emisor_razon_social = models.CharField(max_length=200, default="")
    emisor_direccion_fiscal = models.TextField(default="")
    es_sujeto_pasivo_especial = models.BooleanField(default=False)
    esta_inscrita_rtn = models.BooleanField(default=False)
    cliente_es_residente = models.BooleanField(default=True)
    cliente_identificacion = models.CharField(max_length=50, default="")
    cliente_direccion = models.TextField(default="")
    tipo_operacion = models.CharField(
        max_length=20, choices=TipoOperacion.choices, default=TipoOperacion.VENTA_PROPIA
    )
    moneda_operacion = models.CharField(
        max_length=10, choices=MonedaOperacion.choices, default=MonedaOperacion.DIVISA
    )
    tasa_cambio_bcv = models.DecimalField(max_digits=12, decimal_places=4, blank=True, null=True)
    subtotal_base_gravada = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0.00")
    )
    subtotal_exento = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    subtotal_exportacion = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0.00")
    )
    monto_iva_16 = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    monto_iva_adicional = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0.00")
    )
    monto_igtf = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    monto_total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    saldo_pendiente = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    subtotal_base_gravada_bs = models.DecimalField(
        max_digits=15, decimal_places=2, blank=True, null=True
    )
    subtotal_exento_bs = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    monto_iva_16_bs = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    monto_igtf_bs = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    monto_total_bs = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    tercero_rif = models.CharField(max_length=20, default="")
    tercero_razon_social = models.CharField(max_length=200, default="")
    modalidad_emision = models.CharField(max_length=20, default="")
    firma_digital = models.TextField(blank=True, null=True)
    estado = models.CharField(
        max_length=3, choices=EstadoFactura.choices, default=EstadoFactura.BORRADOR
    )
    archivo_pdf = models.CharField(max_length=100, blank=True, null=True)
    notas = models.TextField(default="")
    agencia = models.ForeignKey("core.Agencia", models.DO_NOTHING, blank=True, null=True)
    asiento_contable_factura_id = models.IntegerField(blank=True, null=True)
    cliente = models.ForeignKey("crm.Cliente", models.DO_NOTHING, blank=True, null=True)
    moneda = models.ForeignKey("common.Moneda", models.DO_NOTHING, blank=True, null=True)
    venta_asociada = models.ForeignKey("bookings.Venta", models.DO_NOTHING, blank=True, null=True)

    def calcular_impuestos_venezuela(self):
        gravada = Decimal("0.00")
        exenta = Decimal("0.00")
        iva_16 = Decimal("0.00")
        for item in self.itemfacturaconsolidada_set.all():
            subtotal_item = item.cantidad * item.precio_unitario
            if (
                item.tipo_servicio
                == ItemFacturaConsolidada.TipoServicio.TRANSPORTE_AEREO_INTERNACIONAL
            ):
                gravada += subtotal_item / Decimal("2")
                exenta += subtotal_item / Decimal("2")
                iva_16 += (subtotal_item / Decimal("2")) * item.alicuota_iva / Decimal("100")
            elif item.es_gravado:
                gravada += subtotal_item
                iva_16 += subtotal_item * item.alicuota_iva / Decimal("100")
            else:
                exenta += subtotal_item
        self.subtotal_base_gravada = gravada
        self.subtotal_exento = exenta
        self.monto_iva_16 = iva_16
        base_igtf = gravada + iva_16
        if self.es_sujeto_pasivo_especial:
            self.monto_igtf = base_igtf * Decimal("0.03")
        else:
            self.monto_igtf = Decimal("0.00")
        self.monto_total = gravada + exenta + iva_16 + self.monto_igtf
        if self.tasa_cambio_bcv:
            self.subtotal_base_gravada_bs = gravada * self.tasa_cambio_bcv
            self.subtotal_exento_bs = exenta * self.tasa_cambio_bcv
            self.monto_iva_16_bs = iva_16 * self.tasa_cambio_bcv
            self.monto_igtf_bs = self.monto_igtf * self.tasa_cambio_bcv
            self.monto_total_bs = self.monto_total * self.tasa_cambio_bcv

    def clean(self):
        if self.tipo_operacion == self.TipoOperacion.INTERMEDIACION:
            if not self.tercero_rif or not self.tercero_razon_social:
                raise ValidationError("Intermediacion requiere tercero_rif y tercero_razon_social")
        if self.moneda_operacion == self.MonedaOperacion.DIVISA and not self.tasa_cambio_bcv:
            raise ValidationError("Facturas en divisa requieren tasa_cambio_bcv")

    class Meta:
        managed = False
        db_table = "finance_facturaconsolidada"


class FacturaFiscal(models.Model):
    class EstadoFiscal(models.TextChoices):
        PENDIENTE = "PEN", "Pendiente"
        EN_PROCESO = "PRO", "En Proceso"
        APROBADA = "APR", "Aprobada"
        RECHAZADA = "REC", "Rechazada"

    class Meta:
        managed = False
        db_table = "finance_facturafiscal"


class FacturaProveedor(models.Model):
    class EstadoFactura(models.TextChoices):
        CONCILIADA = "CON", "Conciliada"
        REQUIERE_REVISION = "REV", "Requiere Revision"

    class Meta:
        managed = False
        db_table = "finance_facturaproveedor"


class GastoOperativo(models.Model):
    id_gasto = models.AutoField(primary_key=True)
    descripcion = models.CharField(max_length=255)
    monto = models.DecimalField(max_digits=12, decimal_places=2)
    fecha = models.DateField()
    categoria = models.CharField(max_length=100, blank=True, null=True)
    comprobante = models.CharField(max_length=100, blank=True, null=True)
    fecha_registro = models.DateTimeField()
    is_deleted = models.BooleanField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    estado_contable = models.CharField(max_length=3)
    error_contable_msg = models.TextField(blank=True, null=True)
    asiento_contable_id = models.IntegerField(blank=True, null=True)
    agencia = models.ForeignKey("core.Agencia", models.DO_NOTHING, blank=True, null=True)
    creado_por = models.ForeignKey("auth.User", models.DO_NOTHING, blank=True, null=True)
    moneda = models.ForeignKey("common.Moneda", models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = "finance_gastooperativo"


class ItemFacturaConsolidada(models.Model):
    class TipoServicio(models.TextChoices):
        TRANSPORTE_AEREO_INTERNACIONAL = "TAI", "Transporte Aereo Internacional"
        TRANSPORTE_AEREO_NACIONAL = "TAN", "Transporte Aereo Nacional"
        ALOJAMIENTO_Y_OTROS_GRAVADOS = "AOG", "Alojamiento y otros"
        COMISION_INTERMEDIACION = "CIN", "Comision Intermediacion"

    id_item_factura = models.AutoField(primary_key=True)
    descripcion = models.CharField(max_length=500, default="")
    cantidad = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("1.00"))
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    subtotal_item = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    tipo_servicio = models.CharField(
        max_length=30,
        choices=TipoServicio.choices,
        default=TipoServicio.ALOJAMIENTO_Y_OTROS_GRAVADOS,
    )
    es_gravado = models.BooleanField(default=True)
    alicuota_iva = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("16.00"))
    nombre_pasajero = models.CharField(max_length=200, blank=True, default="")
    numero_boleto = models.CharField(max_length=50, blank=True, default="")
    itinerario = models.TextField(blank=True, default="")
    codigo_aerolinea = models.CharField(max_length=10, blank=True, default="")
    factura = models.ForeignKey(
        "finance.FacturaConsolidada", models.DO_NOTHING, blank=True, null=True
    )

    def clean(self):
        if self.tipo_servicio in (
            ItemFacturaConsolidada.TipoServicio.TRANSPORTE_AEREO_INTERNACIONAL,
            ItemFacturaConsolidada.TipoServicio.TRANSPORTE_AEREO_NACIONAL,
        ):
            if not self.nombre_pasajero or not self.numero_boleto or not self.itinerario:
                raise ValidationError(
                    "Items de transporte aereo requieren nombre_pasajero, numero_boleto e itinerario"
                )

    class Meta:
        managed = False
        db_table = "finance_itemfacturaconsolidada"


class ItemReporte(models.Model):
    class EstadoConciliacion(models.TextChoices):
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
    agencia = models.ForeignKey("core.Agencia", models.DO_NOTHING, blank=True, null=True)

    class Meta:
        managed = False
        db_table = "finance_itemreporte"


class LineaReporteReconciliacion(models.Model):
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
    agencia = models.ForeignKey("core.Agencia", models.DO_NOTHING, blank=True, null=True)

    def __str__(self):
        return f"{self.numero_boleto_reportado} - ${self.total_cobrado}"

    class Meta:
        managed = False
        db_table = "finance_lineareportereconciliacion"


class LinkDePago(models.Model):
    class EstadoPago(models.TextChoices):
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
    agencia = models.ForeignKey("core.Agencia", models.DO_NOTHING, blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.expira_en:
            self.expira_en = django.utils.timezone.now() + django.utils.timezone.timedelta(hours=24)
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


class LiquidacionAgente(models.Model):
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
    agencia = models.ForeignKey("core.Agencia", models.DO_NOTHING, blank=True, null=True)
    agente = models.ForeignKey("auth.User", models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = "finance_liquidacionagente"
        unique_together = (("agente", "periodo_mes", "periodo_anio"),)


class Moneda(models.Model):
    codigo_iso = models.CharField(max_length=3)
    nombre = models.CharField(max_length=50)
    simbolo = models.CharField(max_length=5)

    class Meta:
        managed = False
        db_table = "finance_moneda"


class PagoBinance(models.Model):
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
    agencia = models.ForeignKey("core.Agencia", models.DO_NOTHING, blank=True, null=True)

    class Meta:
        managed = False
        db_table = "finance_pagobinance"


class PropuestaTransaccionIA(models.Model):
    class EstadoPropuesta(models.TextChoices):
        PENDIENTE = "PEN", "Pendiente"
        RECHAZADA = "REC", "Rechazada"
        APROBADA = "APR", "Aprobada"

    class Meta:
        managed = False
        db_table = "finance_propuestatransaccionia"


class ReglaComision(models.Model):
    class TipoCalculo(models.TextChoices):
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
    agencia = models.ForeignKey("core.Agencia", models.DO_NOTHING, blank=True, null=True)
    agente = models.ForeignKey("auth.User", models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = "finance_reglacomision"
        unique_together = (("agencia", "agente"),)


class ReporteProveedor(models.Model):
    class EstadoReporte(models.TextChoices):
        PENDIENTE = "PEN", "Pendiente"

    id = models.BigAutoField(primary_key=True)
    archivo = models.CharField(max_length=100)
    fecha_carga = models.DateTimeField()
    estado = models.CharField(max_length=3, choices=EstadoReporte.choices)
    total_registros = models.IntegerField()
    total_con_diferencia = models.IntegerField()
    notas = models.TextField()
    agencia = models.ForeignKey("core.Agencia", models.DO_NOTHING, blank=True, null=True)
    proveedor = models.ForeignKey("bookings.Proveedor", models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = "finance_reporteproveedor"


class ReporteReconciliacion(models.Model):
    class Estados(models.TextChoices):
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
        agencia_nombre = self.agencia.nombre if self.agencia else "N/A"
        return f"Reporte {self.proveedor} - {self.fecha_subida.strftime('%d/%m/%Y')} ({agencia_nombre})"

    class Meta:
        managed = False
        db_table = "finance_reportereconciliacion"


class RetencionISLR(models.Model):
    class TipoOperacion(models.TextChoices):
        COMISIONES_MERCANTILES = "CM", "Comisiones Mercantiles"
        HONORARIOS_PROFESIONALES = "HP", "Honorarios Profesionales"
        ARRENDAMIENTO = "AR", "Arrendamiento"
        DIVIDENDOS = "DV", "Dividendos"
        OTROS = "OT", "Otros"

    class Estado(models.TextChoices):
        PENDIENTE = "PEN", "Pendiente"
        APLICADA = "APL", "Aplicada"

    id_retencion = models.AutoField(primary_key=True)
    numero_comprobante = models.CharField(unique=True, max_length=50)
    fecha_emision = models.DateField(default=date.today)
    fecha_operacion = models.DateField(blank=True, null=True)
    periodo_fiscal = models.CharField(max_length=7, blank=True, null=True)
    tipo_operacion = models.CharField(
        max_length=3, choices=TipoOperacion.choices, default=TipoOperacion.COMISIONES_MERCANTILES
    )
    codigo_concepto = models.CharField(max_length=10, default="")
    base_imponible = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    porcentaje_retencion = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal("0.00")
    )
    monto_retenido = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    estado = models.CharField(max_length=3, choices=Estado.choices, default=Estado.PENDIENTE)
    archivo_comprobante = models.CharField(max_length=100, blank=True, null=True)
    observaciones = models.TextField(default="")
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)
    cliente = models.ForeignKey("crm.Cliente", models.DO_NOTHING, blank=True, null=True)
    factura = models.ForeignKey(
        "finance.FacturaConsolidada", models.DO_NOTHING, blank=True, null=True
    )
    agencia = models.ForeignKey("core.Agencia", models.DO_NOTHING, blank=True, null=True)

    def save(self, *args, **kwargs):
        if self.base_imponible is not None and self.porcentaje_retencion:
            self.monto_retenido = self.base_imponible * self.porcentaje_retencion / Decimal("100")
        if self.fecha_emision and not self.periodo_fiscal:
            self.periodo_fiscal = self.fecha_emision.strftime("%Y-%m")
        super().save(*args, **kwargs)

    class Meta:
        managed = False
        db_table = "finance_retencionislr"


class TasaCambio(models.Model):
    id = models.BigAutoField(primary_key=True)
    fecha = models.DateField()
    moneda = models.CharField(max_length=3)
    monto = models.DecimalField(max_digits=10, decimal_places=4)
    ultima_actualizacion = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "finance_tasacambio"
        unique_together = (("fecha", "moneda"),)


class TaxRefundOpportunity(models.Model):
    class Estado(models.TextChoices):
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
    agencia = models.ForeignKey("core.Agencia", models.DO_NOTHING)
    boleto = models.OneToOneField("bookings.BoletoImportado", models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = "finance_taxrefundopportunity"


class TipoCambio(models.Model):
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


class TransaccionPago(models.Model):
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
    agencia = models.ForeignKey("core.Agencia", models.DO_NOTHING, blank=True, null=True)

    class Meta:
        managed = False
        db_table = "finance_transaccionpago"


import logging
from decimal import Decimal

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

# REFACTOR: Nuevos imports
# from apps.crm.models import Cliente # REFACTOR: Usar string 'crm.Cliente'
# from apps.bookings.models import Venta # Circular dependency risk if not careful, use string 'bookings.Venta' or lazy import

from core.models_catalogos import Moneda
# REFACTOR: Usar referencias lazy ('core.AsientoContable') para evitar circulares

logger = logging.getLogger(__name__)

from django.db.models.signals import post_save, pre_save, post_delete
from django.dispatch import receiver




class Factura(models.Model):
    id_factura = models.AutoField(primary_key=True, verbose_name=_("ID Factura"))
    numero_factura = models.CharField(_("Número de Factura"), max_length=50, unique=True, blank=True, help_text=_("Puede ser un correlativo fiscal o interno."))

    # REFACTOR: Apuntar a bookings.Venta
    venta_asociada = models.ForeignKey('bookings.Venta', on_delete=models.SET_NULL, blank=True, null=True, related_name='facturas', verbose_name=_("Venta Asociada"))
    agencia = models.ForeignKey('core.Agencia', on_delete=models.CASCADE, null=True, blank=True, verbose_name=_("Agencia"))
    cliente = models.ForeignKey('crm.Cliente', on_delete=models.PROTECT, verbose_name=_("Cliente"), blank=True, null=True)

    fecha_emision = models.DateField(_("Fecha de Emisión"), default=timezone.now)
    fecha_vencimiento = models.DateField(_("Fecha de Vencimiento"), blank=True, null=True)
    moneda = models.ForeignKey(Moneda, on_delete=models.PROTECT, verbose_name=_("Moneda"))
    subtotal = models.DecimalField(_("Subtotal"), max_digits=12, decimal_places=2, default=0)
    monto_impuestos = models.DecimalField(_("Monto Impuestos"), max_digits=12, decimal_places=2, default=0)
    monto_total = models.DecimalField(_("Monto Total"), max_digits=12, decimal_places=2, editable=False, default=0)
    saldo_pendiente = models.DecimalField(_("Saldo Pendiente"), max_digits=12, decimal_places=2, editable=False, default=0)
    
    class TipoFactura(models.TextChoices):
        PROPIA = 'PRO', _('Factura Propia (Comisión/Servicios)')
        TERCEROS = 'TER', _('Factura por Cuenta de Terceros (Boletos)')
        NOTA_DEBITO = 'ND', _('Nota de Débito')
        NOTA_CREDITO = 'NC', _('Nota de Crédito')

    tipo_factura = models.CharField(_("Tipo de Factura"), max_length=3, choices=TipoFactura.choices, default=TipoFactura.PROPIA)
    numero_control = models.CharField(_("Número de Control"), max_length=50, blank=True, null=True, help_text=_("Número de Control Fiscal obligatorio."))
    
    # Snapshot de cliente (para historico fiscal)
    cliente_nombre = models.CharField(_("Nombre/Razón Social Cliente"), max_length=255, blank=True)
    cliente_rif = models.CharField(_("RIF/Documento Cliente"), max_length=20, blank=True)
    cliente_direccion = models.TextField(_("Dirección Fiscal Cliente"), blank=True)
    cliente_telefono = models.CharField(_("Teléfono Cliente"), max_length=50, blank=True)

    # Convertibilidad (Multimoneda)
    tasa_cambio = models.DecimalField(_("Tasa de Cambio (BCV)"), max_digits=12, decimal_places=4, default=1, help_text=_("Tasa de cambio vigente a la fecha de emisión."))
    moneda_transaccion = models.CharField(_("Moneda Transacción"), max_length=3, default='USD', help_text="Moneda en la que se pagó")

    # Totales Desglosados
    base_imponible = models.DecimalField(_("Base Imponible (Gravada)"), max_digits=12, decimal_places=2, default=0)
    base_exenta = models.DecimalField(_("Base Exenta"), max_digits=12, decimal_places=2, default=0)
    
    iva_porcentaje = models.DecimalField(_("% IVA"), max_digits=5, decimal_places=2, default=16)
    iva_monto = models.DecimalField(_("Monto IVA"), max_digits=12, decimal_places=2, default=0)
    
    igtf_porcentaje = models.DecimalField(_("% IGTF"), max_digits=5, decimal_places=2, default=3)
    igtf_monto = models.DecimalField(_("Monto IGTF"), max_digits=12, decimal_places=2, default=0, help_text=_("Impuesto a Grandes Transacciones Financieras (si aplica)."))
    
    inatur_porcentaje = models.DecimalField(_("% INATUR"), max_digits=5, decimal_places=2, default=1)
    inatur_monto = models.DecimalField(_("Monto INATUR"), max_digits=12, decimal_places=2, default=0, help_text=_("Contribución parafiscal Turismo (1%)."))

    # Relacion para ND/NC
    factura_asociada = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='documentos_relacionados', verbose_name=_("Factura Asociada (Para ND/NC)"))

    class EstadoFactura(models.TextChoices):
        BORRADOR = 'BOR', _('Borrador')
        EMITIDA = 'EMI', _('Emitida (Pendiente de Pago)')
        PARCIAL = 'PAR', _('Pagada Parcialmente')
        PAGADA = 'PAG', _('Pagada Totalmente')
        VENCIDA = 'VEN', _('Vencida')
        ANULADA = 'ANU', _('Anulada')
    
    estado = models.CharField(_("Estado de la Factura"), max_length=3, choices=EstadoFactura.choices, default=EstadoFactura.BORRADOR)
    notas = models.TextField(_("Notas de la Factura"), blank=True, null=True)
    asiento_contable_factura = models.ForeignKey('core.AsientoContable', related_name='finance_facturas_asociadas', on_delete=models.SET_NULL, blank=True, null=True, verbose_name=_("Asiento Contable de Factura"))
    archivo_pdf = models.FileField(_("Archivo PDF"), upload_to='facturas/%Y/%m/', blank=True, null=True)

    class Meta:
        verbose_name = _("Factura de Cliente")
        verbose_name_plural = _("Facturas de Clientes")
        ordering = ['-fecha_emision', '-numero_factura']
        indexes = [
            models.Index(fields=['numero_factura']),
            models.Index(fields=['numero_control']),
            models.Index(fields=['fecha_emision']),
            models.Index(fields=['tipo_factura']),
            models.Index(fields=['agencia', 'fecha_emision']),
            models.Index(fields=['agencia', 'estado']),
            models.Index(fields=['venta_asociada']),
        ]
        db_table = 'core_factura' # MANTENER COMPATIBILIDAD

    def __str__(self):
        return self.numero_factura or f"FACT-{self.id_factura}"

    @property
    def monto_total_bs(self):
        """Conversión del total a Bolívares usando la tasa de la factura."""
        if self.monto_total and self.tasa_cambio > 0:
            return (self.monto_total * self.tasa_cambio).quantize(Decimal("0.01"))
        return Decimal("0.00")



    def recalcular_totales(self):
        """Calcula bases, impuestos y totales basados en los items."""
        # Lógica idéntica al original
        base_gravada = Decimal(0)
        base_exenta = Decimal(0)
        
        items = self.items_factura.all()
        if items.exists():
            for item in items:
                if item.tipo_impuesto == '16' or item.tipo_impuesto == '08':
                    base_gravada += item.subtotal_item
                else:
                    base_exenta += item.subtotal_item
        
        self.base_imponible = base_gravada
        self.base_exenta = base_exenta
        
        self.iva_monto = self.base_imponible * (self.iva_porcentaje / Decimal(100))
        self.subtotal = self.base_imponible + self.base_exenta
        
        # INATUR (1%) sobre el subtotal del servicio turístico
        self.inatur_monto = self.subtotal * (self.inatur_porcentaje / Decimal(100))
        
        # IGTF (3%) sobre el total a pagar en divisas (Subtotal + IVA + INATUR)
        # Nota: En Venezuela el IGTF se calcula sobre el total de la operación si se paga en divisas.
        self.igtf_monto = (self.subtotal + self.iva_monto + self.inatur_monto) * (self.igtf_porcentaje / Decimal(100))
        
        self.monto_impuestos = self.iva_monto + self.igtf_monto + self.inatur_monto
        self.monto_total = self.subtotal + self.monto_impuestos
        
        if self.saldo_pendiente is None or self.estado == self.EstadoFactura.BORRADOR:
            self.saldo_pendiente = self.monto_total

    def get_display_name(self):
        """Devuelve el nombre del cliente o la descripción del primer item como fallback."""
        if self.cliente:
            return self.cliente.get_nombre_completo()
        
        # Fallback al primer item de la venta asociada
        if self.venta_asociada:
            primer_item = self.venta_asociada.items_venta.first()
            if primer_item:
                return primer_item.descripcion_personalizada
        
        return "Cliente no identificado"

    def save(self, *args, **kwargs):
        es_creacion = self.pk is None
        if not self.numero_factura:
            consecutivo = Factura.objects.count() + 1 if es_creacion else self.pk
            self.numero_factura = f"F-{self.fecha_emision.strftime('%Y%m%d')}-{consecutivo:04d}"
        
        # Snapshot cliente
        if self.cliente and not self.cliente_rif:
            try:
                self.cliente_nombre = self.cliente.get_nombre_completo()
                # Ajuste: numero_documento puede ser empty
                self.cliente_rif = getattr(self.cliente, 'numero_documento', '') or ''
                self.cliente_direccion = getattr(self.cliente, 'direccion_linea1', '') or ''
                self.cliente_telefono = self.cliente.telefono_principal or ''
            except Exception:
                pass

        if es_creacion:
             self.monto_total = 0
             self.saldo_pendiente = 0

        super().save(*args, **kwargs)


# Auditoría forense trasladada a core/signals_audit.py


class ItemFactura(models.Model):
    id_item_factura = models.AutoField(primary_key=True, verbose_name=_("ID Item Factura"))
    factura = models.ForeignKey(Factura, related_name='items_factura', on_delete=models.CASCADE, verbose_name=_("Factura"))
    descripcion = models.CharField(_("Descripción del Item"), max_length=500)
    cantidad = models.DecimalField(_("Cantidad"), max_digits=10, decimal_places=2, default=1)
    precio_unitario = models.DecimalField(_("Precio Unitario"), max_digits=12, decimal_places=2)
    subtotal_item = models.DecimalField(_("Subtotal Item"), max_digits=12, decimal_places=2, editable=False)

    class TipoImpuesto(models.TextChoices):
        IVA_16 = '16', _('IVA General (16%)')
        IVA_8 = '08', _('IVA Reducido (8%)')
        EXENTO = '00', _('Exento / No Sujeto')
    tipo_impuesto = models.CharField(_("Tipo Impuesto"), max_length=2, choices=TipoImpuesto.choices, default=TipoImpuesto.IVA_16)

    class Meta:
        verbose_name = _("Item de Factura")
        verbose_name_plural = _("Items de Factura")
        db_table = 'core_itemfactura' # MANTENER COMPATIBILIDAD

    def __str__(self):
        return f"{self.cantidad} x {self.descripcion} en Factura {self.factura.numero_factura}"

    def save(self, *args, **kwargs):
        self.subtotal_item = self.precio_unitario * self.cantidad
        super().save(*args, **kwargs)
        
        try:
            self.factura.recalcular_totales()
            self.factura.save()
        except Exception:
            logger.exception(f"Failed to recalculate totals for Factura {self.factura_id}")

class ReporteProveedor(models.Model):
    class EstadoReporte(models.TextChoices):
        PENDIENTE = 'PEN', _('Pendiente por Procesar')
        PROCESADO = 'PRO', _('Procesado')
        ERROR = 'ERR', _('Error en Procesamiento')

    """
    DEPRECADO: Usar apps.finance.models.reconciliacion.ReporteReconciliacion en su lugar.
    """

    proveedor = models.ForeignKey('core.Proveedor', on_delete=models.CASCADE, related_name='reportes_finance')
    agencia = models.ForeignKey('core.Agencia', on_delete=models.CASCADE, null=True, blank=True, verbose_name=_("Agencia"))
    archivo = models.FileField(_("Archivo de Reporte"), upload_to='finanzas/reportes/%Y/%m/')
    fecha_carga = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(_("Estado"), max_length=3, choices=EstadoReporte.choices, default=EstadoReporte.PENDIENTE)
    
    total_registros = models.IntegerField(default=0)
    total_con_diferencia = models.IntegerField(default=0)
    
    notas = models.TextField(blank=True)

    def __str__(self):
        return f"Reporte {self.proveedor.nombre} - {self.fecha_carga.strftime('%d/%m/%Y')}"

    class Meta:
        verbose_name = _("Reporte de Proveedor")
        verbose_name_plural = _("Reportes de Proveedores")

class ItemReporte(models.Model):
    class EstadoConciliacion(models.TextChoices):
        MATCH = 'MAT', _('Conciliado (OK)')
        DISCREPANCY = 'DIS', _('Discrepancia detectada')
        MISSING_INTERNAL = 'MIN', _('Falta en sistema (Solo en reporte)')
        MISSING_PROVIDER = 'MPR', _('Falta en reporte (Solo en sistema)')

    reporte = models.ForeignKey(ReporteProveedor, on_delete=models.CASCADE, related_name='items')
    numero_boleto = models.CharField(_("Número de Boleto"), max_length=50)
    
    pnr = models.CharField(_("PNR"), max_length=10, blank=True, null=True)
    pasajero = models.CharField(_("Pasajero"), max_length=200, blank=True, null=True)
    fecha_emision = models.DateField(_("Fecha Emisión"), null=True, blank=True)
    
    monto_total_proveedor = models.DecimalField(max_digits=12, decimal_places=2)
    monto_sistema = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax_proveedor = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    comision_proveedor = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Vinculación con registro interno
    boleto_interno = models.ForeignKey('bookings.BoletoImportado', on_delete=models.SET_NULL, null=True, blank=True, related_name='items_reconciliacion')
    
    estado = models.CharField(max_length=3, choices=EstadoConciliacion.choices, default=EstadoConciliacion.MATCH)
    fecha_conciliacion = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.numero_boleto} - {self.estado}"

class DiferenciaFinanciera(models.Model):
    item_reporte = models.ForeignKey(ItemReporte, on_delete=models.CASCADE, related_name='diferencias')
    campo_discrepancia = models.CharField(max_length=50) # 'monto_total', 'tax', 'comision'
    valor_sistema = models.DecimalField(max_digits=12, decimal_places=2)
    valor_proveedor = models.DecimalField(max_digits=12, decimal_places=2)
    diferencia = models.DecimalField(max_digits=12, decimal_places=2)
    
    resuelto = models.BooleanField(default=False)
    fecha_resolucion = models.DateTimeField(null=True, blank=True)

class GastoOperativo(models.Model):
    id_gasto = models.AutoField(primary_key=True, verbose_name=_("ID Gasto"))
    agencia = models.ForeignKey('core.Agencia', on_delete=models.CASCADE, null=True, blank=True, verbose_name=_("Agencia"))
    descripcion = models.CharField(_("Descripción"), max_length=255)
    monto = models.DecimalField(_("Monto"), max_digits=12, decimal_places=2)
    fecha = models.DateField(_("Fecha"), default=timezone.now)
    categoria = models.CharField(_("Categoría"), max_length=100, blank=True, null=True)
    comprobante = models.FileField(_("Comprobante/Factura"), upload_to='gastos/%Y/%m/', blank=True, null=True)
    moneda = models.ForeignKey(Moneda, on_delete=models.PROTECT, verbose_name=_("Moneda"))
    creado_por = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("Registrado por"))
    fecha_registro = models.DateTimeField(auto_now_add=True)
    
    # --- CONTROL CONTABLE (Audit Point 3) ---
    asiento_contable = models.ForeignKey('core.AsientoContable', on_delete=models.SET_NULL, blank=True, null=True, verbose_name=_("Asiento Contable Asociado"))
    
    class EstadoContable(models.TextChoices):
        PENDIENTE = 'PEN', _('Pendiente de Contabilizar')
        PROCESADO = 'PRO', _('Contabilizado Correctamente')
        ERROR = 'ERR', _('Error de Configuración Contable')
        
    estado_contable = models.CharField(_("Estado Contable"), max_length=3, choices=EstadoContable.choices, default=EstadoContable.PENDIENTE)
    error_contable_msg = models.TextField(_("Mensaje de Error Contable"), blank=True, null=True, help_text=_("Indica por qué no se pudo generar el asiento automático."))

    class Meta:
        verbose_name = _("Gasto Operativo")
        verbose_name_plural = _("Gastos Operativos")
        ordering = ['-fecha', '-fecha_registro']
        db_table = 'core_gastooperativo'

    def __str__(self):
        return f"{self.fecha} - {self.descripcion} ({self.monto} {self.moneda})"
class PagoBinance(models.Model):
    class EstadoPago(models.TextChoices):
        INICIAL = 'INI', _('Inicial / Pendiente')
        PROCESANDO = 'PRO', _('Procesando')
        EXITOSO = 'EXI', _('Exitoso')
        FALLIDO = 'FAL', _('Fallido')
        EXPIRADO = 'EXP', _('Expirado')

    id_pago_binance = models.AutoField(primary_key=True)
    factura = models.ForeignKey(Factura, on_delete=models.CASCADE, related_name='pagos_binance', verbose_name=_("Factura"))
    
    # Binance Specifics
    prepay_id = models.CharField(_("Binance Prepay ID"), max_length=100, blank=True, null=True)
    merchant_trade_no = models.CharField(_("Internal Trade Number"), max_length=50, unique=True)
    checkout_url = models.URLField(_("Checkout URL"), max_length=500, blank=True, null=True)
    
    monto = models.DecimalField(_("Monto"), max_digits=12, decimal_places=2)
    moneda = models.CharField(_("Moneda"), max_length=5, default="USDT")
    
    estado = models.CharField(_("Estado"), max_length=3, choices=EstadoPago.choices, default=EstadoPago.INICIAL)
    
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    raw_response = models.JSONField(_("Respuesta API Binance"), default=dict, blank=True)

    class Meta:
        verbose_name = _("Pago Binance Pay")
        verbose_name_plural = _("Pagos Binance Pay")
        ordering = ['-fecha_creacion']

    def __str__(self):
        return f"Pago {self.merchant_trade_no} - {self.factura.numero_factura} ({self.get_estado_display()})"


class TransaccionPago(models.Model):
    """
    Modelo blindado para registrar pagos provenientes de Webhooks externos.
    La clave es 'webhook_transaction_id' con unique=True para garantizar idempotencia.
    """
    class ProveedorPago(models.TextChoices):
        BINANCE = 'BIN', _('Binance Pay')
        STRIPE = 'STR', _('Stripe')
        ZELLE = 'ZEL', _('Zelle')
        OTRO = 'OTR', _('Otro')

    id_transaccion = models.AutoField(primary_key=True)
    proveedor = models.CharField(_("Proveedor"), max_length=3, choices=ProveedorPago.choices)
    monto = models.DecimalField(_("Monto"), max_digits=12, decimal_places=2)
    moneda = models.CharField(_("Moneda"), max_length=10, default='USD')
    
    # Vinculación con la venta (Uso de string para evitar circularidad)
    venta = models.ForeignKey('bookings.Venta', on_delete=models.CASCADE, related_name='transacciones_pago', verbose_name=_("Venta"))
    
    # El campo más importante para el blindaje
    webhook_transaction_id = models.CharField(
        _("Webhook Transaction ID"), 
        max_length=255, 
        unique=True, 
        db_index=True,
        help_text=_("ID único de la pasarela (ej. TransactionID de Binance o pi_XXX de Stripe).")
    )
    
    data_raw = models.JSONField(_("Datos Raw del Webhook"), default=dict, blank=True)
    fecha_registro = models.DateTimeField(_("Fecha Registro"), auto_now_add=True)

    class Meta:
        verbose_name = _("Transacción de Pago")
        verbose_name_plural = _("Transacciones de Pago")
        ordering = ['-fecha_registro']

    def __str__(self):
        return f"{self.get_proveedor_display()} - {self.webhook_transaction_id}"

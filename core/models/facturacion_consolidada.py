# core/models/facturacion_consolidada.py
"""
Modelo consolidado de facturación para Venezuela
Cumple con: Providencias SENIAT 0071, 0032, 102, 121
Ley de IVA, Ley IGTF, Ley Orgánica de Turismo
"""
import logging
from decimal import Decimal

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from personas.models import Cliente
from core.models_catalogos import Moneda
from .contabilidad import AsientoContable

logger = logging.getLogger(__name__)


class FacturaConsolidada(models.Model):
    """Factura consolidada con normativa venezolana completa"""
    
    # === IDENTIFICACIÓN ===
    id_factura = models.AutoField(primary_key=True, verbose_name=_("ID Factura"))
    numero_factura = models.CharField(_("Número de Factura"), max_length=50, unique=True, blank=True)
    numero_control = models.CharField(_("Número de Control Fiscal"), max_length=50, blank=True, 
                                     help_text=_("Asignado por imprenta digital autorizada"))
    
    # === RELACIONES ===
    venta_asociada = models.ForeignKey('Venta', on_delete=models.SET_NULL, blank=True, null=True, 
                                      related_name='facturas_consolidadas', verbose_name=_("Venta Asociada"))
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, verbose_name=_("Cliente"))
    moneda = models.ForeignKey(Moneda, on_delete=models.PROTECT, verbose_name=_("Moneda"))
    
    # === FECHAS ===
    fecha_emision = models.DateField(_("Fecha de Emisión"), default=timezone.now)
    fecha_vencimiento = models.DateField(_("Fecha de Vencimiento"), blank=True, null=True)
    
    # === EMISOR (AGENCIA) ===
    emisor_rif = models.CharField(_("RIF Emisor"), max_length=20)
    emisor_razon_social = models.CharField(_("Razón Social Emisor"), max_length=200)
    emisor_direccion_fiscal = models.TextField(_("Dirección Fiscal Emisor"))
    es_sujeto_pasivo_especial = models.BooleanField(_("Es Sujeto Pasivo Especial"), default=False,
                                                    help_text=_("Determina obligaciones como agente de percepción IGTF"))
    esta_inscrita_rtn = models.BooleanField(_("Inscrita en RTN"), default=False,
                                           help_text=_("Registro Turístico Nacional"))
    
    # === CLIENTE ===
    cliente_es_residente = models.BooleanField(_("Cliente es Residente"), default=True,
                                              help_text=_("Determina si aplica exportación de servicios (alícuota 0%)"))
    cliente_identificacion = models.CharField(_("Identificación Cliente"), max_length=50,
                                             help_text=_("Cédula, RIF o Pasaporte"))
    cliente_direccion = models.TextField(_("Dirección Cliente"), blank=True)
    
    # === TIPO DE OPERACIÓN ===
    class TipoOperacion(models.TextChoices):
        VENTA_PROPIA = 'VENTA_PROPIA', _('Venta Propia')
        INTERMEDIACION = 'INTERMEDIACION', _('Intermediación')
    
    tipo_operacion = models.CharField(_("Tipo de Operación"), max_length=20, 
                                     choices=TipoOperacion.choices,
                                     help_text=_("Determina tratamiento fiscal (Art. 10 Ley IVA)"))
    
    # === MONEDA Y CAMBIO ===
    class MonedaOperacion(models.TextChoices):
        BOLIVAR = 'BOLIVAR', _('Bolívar')
        DIVISA = 'DIVISA', _('Divisa')
    
    moneda_operacion = models.CharField(_("Moneda de Operación"), max_length=10,
                                       choices=MonedaOperacion.choices,
                                       help_text=_("Moneda en que se pacta y cobra la operación"))
    tasa_cambio_bcv = models.DecimalField(_("Tasa de Cambio BCV"), max_digits=12, decimal_places=4,
                                         blank=True, null=True,
                                         help_text=_("Tasa oficial BCV del día de la operación"))
    
    # === BASES IMPONIBLES (MONEDA FUNCIONAL USD) ===
    subtotal_base_gravada = models.DecimalField(_("Base Gravada 16%"), max_digits=12, decimal_places=2, default=0,
                                               help_text=_("Servicios gravados con alícuota general"))
    subtotal_exento = models.DecimalField(_("Base Exenta"), max_digits=12, decimal_places=2, default=0,
                                         help_text=_("Servicios exentos (ej: transporte aéreo nacional)"))
    subtotal_exportacion = models.DecimalField(_("Base Exportación 0%"), max_digits=12, decimal_places=2, default=0,
                                              help_text=_("Servicios a no residentes (turismo receptivo)"))
    
    # === IMPUESTOS (MONEDA FUNCIONAL USD) ===
    monto_iva_16 = models.DecimalField(_("IVA 16%"), max_digits=12, decimal_places=2, default=0)
    monto_iva_adicional = models.DecimalField(_("IVA Adicional Divisas"), max_digits=12, decimal_places=2, default=0,
                                             help_text=_("Alícuota adicional 5-25% sobre exentos pagados en divisas"))
    monto_igtf = models.DecimalField(_("IGTF 3%"), max_digits=12, decimal_places=2, default=0,
                                    help_text=_("Impuesto a Grandes Transacciones Financieras"))
    
    # === TOTALES (MONEDA FUNCIONAL USD) ===
    subtotal = models.DecimalField(_("Subtotal"), max_digits=12, decimal_places=2, default=0, editable=False)
    monto_total = models.DecimalField(_("Monto Total"), max_digits=12, decimal_places=2, default=0, editable=False)
    saldo_pendiente = models.DecimalField(_("Saldo Pendiente"), max_digits=12, decimal_places=2, default=0, editable=False)
    
    # === EQUIVALENTES EN BOLÍVARES (MONEDA DE PRESENTACIÓN BSD) ===
    subtotal_base_gravada_bs = models.DecimalField(_("Base Gravada Bs"), max_digits=15, decimal_places=2, blank=True, null=True)
    subtotal_exento_bs = models.DecimalField(_("Base Exenta Bs"), max_digits=15, decimal_places=2, blank=True, null=True)
    monto_iva_16_bs = models.DecimalField(_("IVA 16% Bs"), max_digits=15, decimal_places=2, blank=True, null=True)
    monto_igtf_bs = models.DecimalField(_("IGTF Bs"), max_digits=15, decimal_places=2, blank=True, null=True)
    monto_total_bs = models.DecimalField(_("Total Bs"), max_digits=15, decimal_places=2, blank=True, null=True)
    
    # === INTERMEDIACIÓN (ART. 10 LEY IVA) ===
    tercero_rif = models.CharField(_("RIF Tercero"), max_length=20, blank=True,
                                  help_text=_("RIF de la aerolínea u otro proveedor"))
    tercero_razon_social = models.CharField(_("Razón Social Tercero"), max_length=200, blank=True)
    
    # === DIGITAL ===
    class ModalidadEmision(models.TextChoices):
        DIGITAL = 'DIGITAL', _('Digital')
        CONTINGENCIA_FISICA = 'CONTINGENCIA_FISICA', _('Contingencia Física')
    
    modalidad_emision = models.CharField(_("Modalidad de Emisión"), max_length=20,
                                        choices=ModalidadEmision.choices, default=ModalidadEmision.DIGITAL)
    firma_digital = models.TextField(_("Firma Digital"), blank=True, null=True,
                                    help_text=_("Firma electrónica con certificado digital válido"))
    
    # === ESTADO ===
    class EstadoFactura(models.TextChoices):
        BORRADOR = 'BOR', _('Borrador')
        EMITIDA = 'EMI', _('Emitida')
        PARCIAL = 'PAR', _('Pagada Parcialmente')
        PAGADA = 'PAG', _('Pagada Totalmente')
        VENCIDA = 'VEN', _('Vencida')
        ANULADA = 'ANU', _('Anulada')
    
    estado = models.CharField(_("Estado de la Factura"), max_length=3,
                            choices=EstadoFactura.choices, default=EstadoFactura.BORRADOR)
    
    # === ARCHIVOS ===
    archivo_pdf = models.FileField(_("Archivo PDF"), upload_to='facturas/%Y/%m/', blank=True, null=True)
    
    # === CONTABILIDAD ===
    asiento_contable_factura = models.ForeignKey(AsientoContable, related_name='facturas_consolidadas_asociadas',
                                                 on_delete=models.SET_NULL, blank=True, null=True,
                                                 verbose_name=_("Asiento Contable de Factura"))
    
    # === NOTAS ===
    notas = models.TextField(_("Notas de la Factura"), blank=True)
    
    class Meta:
        verbose_name = _("Factura de Cliente")
        verbose_name_plural = _("Facturas de Clientes")
        ordering = ['-fecha_emision', '-numero_factura']
    
    def __str__(self):
        return self.numero_factura or f"FACT-{self.id_factura}"
    
    def save(self, *args, **kwargs):
        # Generar número de factura
        if not self.numero_factura:
            consecutivo = FacturaConsolidada.objects.count() + 1
            self.numero_factura = f"F-{self.fecha_emision.strftime('%Y%m%d')}-{consecutivo:04d}"
        
        # Calcular totales en USD
        self.subtotal = self.subtotal_base_gravada + self.subtotal_exento + self.subtotal_exportacion
        self.monto_total = self.subtotal + self.monto_iva_16 + self.monto_iva_adicional + self.monto_igtf
        
        # Convertir a Bolívares si hay tasa
        if self.tasa_cambio_bcv:
            self.subtotal_base_gravada_bs = self.subtotal_base_gravada * self.tasa_cambio_bcv
            self.subtotal_exento_bs = self.subtotal_exento * self.tasa_cambio_bcv
            self.monto_iva_16_bs = self.monto_iva_16 * self.tasa_cambio_bcv
            self.monto_igtf_bs = self.monto_igtf * self.tasa_cambio_bcv
            self.monto_total_bs = self.monto_total * self.tasa_cambio_bcv
        
        # Inicializar saldo pendiente
        if self.pk is None:
            self.saldo_pendiente = self.monto_total
        
        # Actualizar estado según saldo
        if self.estado in {self.EstadoFactura.BORRADOR, self.EstadoFactura.EMITIDA, 
                          self.EstadoFactura.PARCIAL, self.EstadoFactura.PAGADA}:
            if self.saldo_pendiente <= 0 and self.monto_total > 0:
                self.estado = self.EstadoFactura.PAGADA
            elif 0 < self.saldo_pendiente < self.monto_total:
                self.estado = self.EstadoFactura.PARCIAL
            elif self.estado == self.EstadoFactura.BORRADOR and self.monto_total > 0:
                self.estado = self.EstadoFactura.EMITIDA
        
        super().save(*args, **kwargs)
    
    def recalcular_totales(self):
        """Recalcula totales desde los items"""
        items = self.items_factura.all()
        
        # Resetear bases
        self.subtotal_base_gravada = Decimal('0.00')
        self.subtotal_exento = Decimal('0.00')
        self.subtotal_exportacion = Decimal('0.00')
        self.monto_iva_16 = Decimal('0.00')
        
        # Sumar por tipo de servicio
        for item in items:
            if item.tipo_servicio == ItemFacturaConsolidada.TipoServicio.SERVICIO_EXPORTACION:
                self.subtotal_exportacion += item.subtotal_item
            elif item.tipo_servicio == ItemFacturaConsolidada.TipoServicio.TRANSPORTE_AEREO_NACIONAL:
                self.subtotal_exento += item.subtotal_item
            else:
                self.subtotal_base_gravada += item.subtotal_item
                if item.es_gravado:
                    self.monto_iva_16 += item.subtotal_item * (item.alicuota_iva / 100)
        
        self.save()


class ItemFacturaConsolidada(models.Model):
    """Item de factura con campos específicos para Venezuela"""
    
    id_item_factura = models.AutoField(primary_key=True, verbose_name=_("ID Item Factura"))
    factura = models.ForeignKey(FacturaConsolidada, related_name='items_factura',
                               on_delete=models.CASCADE, verbose_name=_("Factura"))
    
    # === DESCRIPCIÓN ===
    descripcion = models.CharField(_("Descripción del Item"), max_length=500)
    cantidad = models.DecimalField(_("Cantidad"), max_digits=10, decimal_places=2, default=1)
    precio_unitario = models.DecimalField(_("Precio Unitario"), max_digits=12, decimal_places=2)
    subtotal_item = models.DecimalField(_("Subtotal Item"), max_digits=12, decimal_places=2, editable=False)
    
    # === TIPO DE SERVICIO (DETERMINA TRATAMIENTO FISCAL) ===
    class TipoServicio(models.TextChoices):
        COMISION_INTERMEDIACION = 'COMISION_INTERMEDIACION', _('Comisión Intermediación')
        TRANSPORTE_AEREO_NACIONAL = 'TRANSPORTE_AEREO_NACIONAL', _('Transporte Aéreo Nacional')
        ALOJAMIENTO_Y_OTROS_GRAVADOS = 'ALOJAMIENTO_Y_OTROS_GRAVADOS', _('Alojamiento y Otros Gravados')
        SERVICIO_EXPORTACION = 'SERVICIO_EXPORTACION', _('Servicio Exportación')
    
    tipo_servicio = models.CharField(_("Tipo de Servicio"), max_length=30,
                                    choices=TipoServicio.choices,
                                    default=TipoServicio.ALOJAMIENTO_Y_OTROS_GRAVADOS,
                                    help_text=_("Determina tratamiento fiscal del item"))
    
    # === IVA ===
    es_gravado = models.BooleanField(_("Es Gravado"), default=True, help_text=_("Si aplica IVA al item"))
    alicuota_iva = models.DecimalField(_("Alícuota IVA"), max_digits=5, decimal_places=2, default=Decimal('16.00'),
                                      help_text=_("Porcentaje de IVA aplicable"))
    
    # === DATOS ESPECÍFICOS PARA BOLETOS AÉREOS (PROVIDENCIA 0032) ===
    nombre_pasajero = models.CharField(_("Nombre Pasajero"), max_length=200, blank=True,
                                      help_text=_("Obligatorio para boletos aéreos"))
    numero_boleto = models.CharField(_("Número Boleto"), max_length=50, blank=True,
                                    help_text=_("Número del boleto de pasaje"))
    itinerario = models.TextField(_("Itinerario"), blank=True,
                                 help_text=_("Ruta del viaje (ej: CCS-MIA-CCS)"))
    codigo_aerolinea = models.CharField(_("Código Aerolínea"), max_length=10, blank=True,
                                       help_text=_("Código IATA de la aerolínea"))
    
    class Meta:
        verbose_name = _("Item de Factura")
        verbose_name_plural = _("Items de Factura")
    
    def __str__(self):
        return f"{self.cantidad} x {self.descripcion} en {self.factura.numero_factura}"
    
    def save(self, *args, **kwargs):
        # Calcular subtotal
        self.subtotal_item = self.precio_unitario * self.cantidad
        super().save(*args, **kwargs)
        
        # Recalcular totales de factura
        try:
            self.factura.recalcular_totales()
        except Exception as e:
            logger.exception(f"Error recalculando totales de factura {self.factura_id}: {e}")


class DocumentoExportacionConsolidado(models.Model):
    """Documentos de soporte para exportación de servicios (turismo receptivo)"""
    
    class TipoDocumento(models.TextChoices):
        PASAPORTE = 'PASAPORTE', _('Pasaporte')
        COMPROBANTE_PAGO = 'COMPROBANTE_PAGO', _('Comprobante Pago Internacional')
        OTRO = 'OTRO', _('Otro')
    
    factura = models.ForeignKey(FacturaConsolidada, related_name='documentos_exportacion',
                               on_delete=models.CASCADE)
    tipo_documento = models.CharField(_("Tipo Documento"), max_length=20, choices=TipoDocumento.choices)
    numero_documento = models.CharField(_("Número Documento"), max_length=100)
    archivo = models.FileField(_("Archivo"), upload_to='documentos_exportacion/%Y/%m/')
    fecha_subida = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = _("Documento Exportación")
        verbose_name_plural = _("Documentos Exportación")
    
    def __str__(self):
        return f"{self.get_tipo_documento_display()} - {self.numero_documento}"

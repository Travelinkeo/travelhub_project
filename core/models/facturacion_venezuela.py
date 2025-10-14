# Archivo: core/models/facturacion_venezuela.py
"""
Extensión del modelo de facturación para cumplir con la normativa fiscal venezolana.
Incluye campos específicos para agencias de viajes según Providencias 102, 121 y normativa IVA/IGTF.
"""

import logging
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .facturacion import Factura, ItemFactura

logger = logging.getLogger(__name__)


class FacturaVenezuela(Factura):
    """
    Extensión del modelo Factura para cumplir con normativa fiscal venezolana.
    Hereda de Factura base y añade campos específicos requeridos por SENIAT.
    """
    
    class TipoOperacion(models.TextChoices):
        VENTA_PROPIA = 'VENTA_PROPIA', _('Venta Propia')
        INTERMEDIACION = 'INTERMEDIACION', _('Intermediación')
    
    class MonedaOperacion(models.TextChoices):
        BOLIVAR = 'BOLIVAR', _('Bolívar')
        DIVISA = 'DIVISA', _('Divisa')
    
    class ModalidadEmision(models.TextChoices):
        DIGITAL = 'DIGITAL', _('Digital')
        CONTINGENCIA_FISICA = 'CONTINGENCIA_FISICA', _('Contingencia Física')
    
    # === CAMPOS OBLIGATORIOS VENEZUELA ===
    numero_control = models.CharField(
        _("Número de Control Fiscal"), 
        max_length=50, 
        blank=True,
        help_text=_("Número asignado por imprenta digital autorizada")
    )
    
    modalidad_emision = models.CharField(
        _("Modalidad de Emisión"), 
        max_length=20, 
        choices=ModalidadEmision.choices, 
        default=ModalidadEmision.DIGITAL
    )
    
    firma_digital = models.TextField(
        _("Firma Digital"), 
        blank=True, 
        null=True,
        help_text=_("Firma electrónica con certificado digital válido")
    )
    
    # === INFORMACIÓN FISCAL DEL EMISOR (AGENCIA) ===
    emisor_rif = models.CharField(_("RIF Emisor"), max_length=20)
    emisor_razon_social = models.CharField(_("Razón Social Emisor"), max_length=200)
    emisor_direccion_fiscal = models.TextField(_("Dirección Fiscal Emisor"))
    es_sujeto_pasivo_especial = models.BooleanField(
        _("Es Sujeto Pasivo Especial"), 
        default=False,
        help_text=_("Determina obligaciones como agente de percepción IGTF")
    )
    esta_inscrita_rtn = models.BooleanField(
        _("Inscrita en RTN"), 
        default=False,
        help_text=_("Registro Turístico Nacional")
    )
    
    # === INFORMACIÓN DEL CLIENTE ===
    cliente_es_residente = models.BooleanField(
        _("Cliente es Residente"), 
        default=True,
        help_text=_("Determina si aplica exportación de servicios (alícuota 0%)")
    )
    cliente_identificacion = models.CharField(
        _("Identificación Cliente"), 
        max_length=50,
        help_text=_("Cédula, RIF o Pasaporte")
    )
    cliente_direccion = models.TextField(_("Dirección Cliente"), blank=True)
    
    # === OPERACIÓN Y MONEDA ===
    tipo_operacion = models.CharField(
        _("Tipo de Operación"), 
        max_length=20, 
        choices=TipoOperacion.choices,
        help_text=_("Determina tratamiento fiscal (Art. 10 Ley IVA)")
    )
    
    moneda_operacion = models.CharField(
        _("Moneda de Operación"), 
        max_length=10, 
        choices=MonedaOperacion.choices,
        help_text=_("Moneda en que se pacta y cobra la operación")
    )
    
    tasa_cambio_bcv = models.DecimalField(
        _("Tasa de Cambio BCV"), 
        max_digits=12, 
        decimal_places=4, 
        null=True, 
        blank=True,
        help_text=_("Tasa oficial BCV del día de la operación")
    )
    
    # === BASES IMPONIBLES SEGREGADAS ===
    subtotal_base_gravada = models.DecimalField(
        _("Base Gravada 16%"), 
        max_digits=12, 
        decimal_places=2, 
        default=0,
        help_text=_("Servicios gravados con alícuota general")
    )
    
    subtotal_exento = models.DecimalField(
        _("Base Exenta"), 
        max_digits=12, 
        decimal_places=2, 
        default=0,
        help_text=_("Servicios exentos (ej: transporte aéreo nacional)")
    )
    
    subtotal_exportacion = models.DecimalField(
        _("Base Exportación 0%"), 
        max_digits=12, 
        decimal_places=2, 
        default=0,
        help_text=_("Servicios a no residentes (turismo receptivo)")
    )
    
    # === IMPUESTOS CALCULADOS ===
    monto_iva_16 = models.DecimalField(
        _("IVA 16%"), 
        max_digits=12, 
        decimal_places=2, 
        default=0
    )
    
    monto_iva_adicional = models.DecimalField(
        _("IVA Adicional Divisas"), 
        max_digits=12, 
        decimal_places=2, 
        default=0,
        help_text=_("Alícuota adicional 5-25% sobre exentos pagados en divisas")
    )
    
    monto_igtf = models.DecimalField(
        _("IGTF 3%"), 
        max_digits=12, 
        decimal_places=2, 
        default=0,
        help_text=_("Impuesto a Grandes Transacciones Financieras")
    )
    
    # === DATOS DEL TERCERO (INTERMEDIACIÓN) ===
    tercero_rif = models.CharField(
        _("RIF Tercero"), 
        max_length=20, 
        blank=True,
        help_text=_("RIF de la aerolínea u otro proveedor")
    )
    
    tercero_razon_social = models.CharField(
        _("Razón Social Tercero"), 
        max_length=200, 
        blank=True
    )
    
    # === EQUIVALENCIAS EN BOLÍVARES (SI FACTURA EN DIVISAS) ===
    subtotal_base_gravada_bs = models.DecimalField(
        _("Base Gravada Bs"), 
        max_digits=15, 
        decimal_places=2, 
        null=True, 
        blank=True
    )
    
    subtotal_exento_bs = models.DecimalField(
        _("Base Exenta Bs"), 
        max_digits=15, 
        decimal_places=2, 
        null=True, 
        blank=True
    )
    
    monto_iva_16_bs = models.DecimalField(
        _("IVA 16% Bs"), 
        max_digits=15, 
        decimal_places=2, 
        null=True, 
        blank=True
    )
    
    monto_igtf_bs = models.DecimalField(
        _("IGTF Bs"), 
        max_digits=15, 
        decimal_places=2, 
        null=True, 
        blank=True
    )
    
    monto_total_bs = models.DecimalField(
        _("Total Bs"), 
        max_digits=15, 
        decimal_places=2, 
        null=True, 
        blank=True
    )
    
    class Meta:
        verbose_name = _("Factura Venezuela")
        verbose_name_plural = _("Facturas Venezuela")
        ordering = ['-fecha_emision', '-numero_factura']
    
    def calcular_impuestos_venezuela(self):
        """
        Método principal para calcular todos los impuestos según normativa venezolana.
        Implementa la lógica fiscal específica para agencias de viajes.
        """
        try:
            # 1. Calcular bases imponibles por tipo de servicio
            self._calcular_bases_imponibles()
            
            # 2. Calcular IVA según tipo de servicio y residencia del cliente
            self._calcular_iva()
            
            # 3. Calcular alícuota adicional si pago en divisas sobre exentos
            self._calcular_alicuota_adicional()
            
            # 4. Calcular IGTF si aplica (SPE + pago en divisas)
            self._calcular_igtf()
            
            # 5. Calcular equivalencias en bolívares si factura en divisas
            self._calcular_equivalencias_bolivares()
            
            # 6. Actualizar totales
            self._actualizar_totales()
            
            logger.info(f"Impuestos calculados para factura {self.numero_factura}")
            
        except Exception as e:
            logger.error(f"Error calculando impuestos factura {self.numero_factura}: {e}")
            raise
    
    def _calcular_bases_imponibles(self):
        """Clasifica items según tipo de servicio para determinar bases imponibles"""
        self.subtotal_base_gravada = Decimal('0.00')
        self.subtotal_exento = Decimal('0.00')
        self.subtotal_exportacion = Decimal('0.00')
        
        for item in self.items_factura.all():
            item_venezuela = ItemFacturaVenezuela.objects.get(pk=item.pk)
            
            if item_venezuela.tipo_servicio == ItemFacturaVenezuela.TipoServicio.TRANSPORTE_AEREO_NACIONAL:
                self.subtotal_exento += item.subtotal_item
            elif (item_venezuela.tipo_servicio == ItemFacturaVenezuela.TipoServicio.SERVICIO_EXPORTACION 
                  or not self.cliente_es_residente):
                self.subtotal_exportacion += item.subtotal_item
            else:
                self.subtotal_base_gravada += item.subtotal_item
    
    def _calcular_iva(self):
        """Calcula IVA según bases imponibles y tipo de operación"""
        # IVA 16% sobre base gravada
        self.monto_iva_16 = self.subtotal_base_gravada * Decimal('0.16')
        
        # IVA 0% sobre exportaciones (se registra pero es 0)
        # Los servicios exentos no generan IVA
    
    def _calcular_alicuota_adicional(self):
        """
        Calcula alícuota adicional (5-25%) sobre servicios exentos pagados en divisas.
        Según Art. 62 Ley IVA: servicios exentos pierden exención si se pagan en divisas.
        NOTA: Por ahora no aplicamos esta alícuota automáticamente, debe configurarse manualmente.
        """
        # Por ahora no aplicamos automáticamente la alícuota adicional
        # Esto debe ser configurado manualmente según las regulaciones específicas
        self.monto_iva_adicional = Decimal('0.00')
    
    def _calcular_igtf(self):
        """
        Calcula IGTF si la agencia es SPE y el pago es en divisas.
        CRÍTICO: Base IGTF = Subtotal + IVA (impuesto sobre impuesto)
        """
        if (self.es_sujeto_pasivo_especial and 
            self.moneda_operacion == self.MonedaOperacion.DIVISA):
            
            # Base IGTF = Subtotal + IVA (todos los componentes)
            base_igtf = (self.subtotal_base_gravada + self.subtotal_exento + 
                        self.subtotal_exportacion + self.monto_iva_16 + self.monto_iva_adicional)
            
            self.monto_igtf = base_igtf * Decimal('0.03')  # 3%
        else:
            self.monto_igtf = Decimal('0.00')
    
    def _calcular_equivalencias_bolivares(self):
        """Calcula equivalencias en bolívares si la factura es en divisas"""
        if (self.moneda_operacion == self.MonedaOperacion.DIVISA and 
            self.tasa_cambio_bcv):
            
            tasa = self.tasa_cambio_bcv
            self.subtotal_base_gravada_bs = self.subtotal_base_gravada * tasa
            self.subtotal_exento_bs = self.subtotal_exento * tasa
            self.monto_iva_16_bs = self.monto_iva_16 * tasa
            self.monto_igtf_bs = self.monto_igtf * tasa
            self.monto_total_bs = self.monto_total * tasa if self.monto_total else None
    
    def _actualizar_totales(self):
        """Actualiza los totales de la factura con todos los impuestos"""
        # Total = Subtotales + IVA + IGTF
        total_subtotales = (self.subtotal_base_gravada + self.subtotal_exento + 
                           self.subtotal_exportacion)
        total_impuestos = self.monto_iva_16 + self.monto_iva_adicional + self.monto_igtf
        
        self.subtotal = total_subtotales
        self.monto_impuestos = total_impuestos
        self.monto_total = total_subtotales + total_impuestos
        self.saldo_pendiente = self.monto_total
    
    def clean(self):
        """Validaciones específicas para facturación venezolana"""
        super().clean()
        errors = {}
        
        # Validar datos obligatorios según tipo de operación
        if self.tipo_operacion == self.TipoOperacion.INTERMEDIACION:
            if not self.tercero_rif or not self.tercero_razon_social:
                errors['tercero_rif'] = _('Datos del tercero obligatorios en intermediación')
        
        # Validar tasa de cambio si factura en divisas
        if (self.moneda_operacion == self.MonedaOperacion.DIVISA and 
            not self.tasa_cambio_bcv):
            errors['tasa_cambio_bcv'] = _('Tasa BCV obligatoria para facturas en divisas')
        
        # Validar datos fiscales del emisor
        if not self.emisor_rif:
            errors['emisor_rif'] = _('RIF del emisor es obligatorio')
        
        if errors:
            raise ValidationError(errors)
    
    def save(self, *args, **kwargs):
        # Calcular impuestos antes de guardar
        if self.pk:  # Solo si ya existe (tiene items)
            self.calcular_impuestos_venezuela()
        
        super().save(*args, **kwargs)


class ItemFacturaVenezuela(ItemFactura):
    """
    Extensión del modelo ItemFactura para campos específicos de Venezuela.
    """
    
    class TipoServicio(models.TextChoices):
        COMISION_INTERMEDIACION = 'COMISION_INTERMEDIACION', _('Comisión Intermediación')
        TRANSPORTE_AEREO_NACIONAL = 'TRANSPORTE_AEREO_NACIONAL', _('Transporte Aéreo Nacional')
        ALOJAMIENTO_Y_OTROS_GRAVADOS = 'ALOJAMIENTO_Y_OTROS_GRAVADOS', _('Alojamiento y Otros Gravados')
        SERVICIO_EXPORTACION = 'SERVICIO_EXPORTACION', _('Servicio Exportación')
    
    # === CLASIFICACIÓN FISCAL ===
    tipo_servicio = models.CharField(
        _("Tipo de Servicio"), 
        max_length=30, 
        choices=TipoServicio.choices,
        default=TipoServicio.ALOJAMIENTO_Y_OTROS_GRAVADOS,
        help_text=_("Determina tratamiento fiscal del item")
    )
    
    es_gravado = models.BooleanField(
        _("Es Gravado"), 
        default=True,
        help_text=_("Si aplica IVA al item")
    )
    
    alicuota_iva = models.DecimalField(
        _("Alícuota IVA"), 
        max_digits=5, 
        decimal_places=2, 
        default=Decimal('16.00'),
        help_text=_("Porcentaje de IVA aplicable")
    )
    
    # === DATOS ESPECÍFICOS BOLETOS AÉREOS ===
    nombre_pasajero = models.CharField(
        _("Nombre Pasajero"), 
        max_length=200, 
        blank=True,
        help_text=_("Obligatorio para boletos aéreos")
    )
    
    numero_boleto = models.CharField(
        _("Número Boleto"), 
        max_length=50, 
        blank=True,
        help_text=_("Número del boleto de pasaje")
    )
    
    itinerario = models.TextField(
        _("Itinerario"), 
        blank=True,
        help_text=_("Ruta del viaje (ej: CCS-MIA-CCS)")
    )
    
    codigo_aerolinea = models.CharField(
        _("Código Aerolínea"), 
        max_length=10, 
        blank=True,
        help_text=_("Código IATA de la aerolínea")
    )
    
    class Meta:
        verbose_name = _("Item Factura Venezuela")
        verbose_name_plural = _("Items Factura Venezuela")
    
    def clean(self):
        """Validaciones específicas para items de factura venezolana"""
        super().clean()
        errors = {}
        
        # Validar datos obligatorios para boletos aéreos
        if self.tipo_servicio in [self.TipoServicio.TRANSPORTE_AEREO_NACIONAL]:
            if not self.nombre_pasajero:
                errors['nombre_pasajero'] = _('Nombre del pasajero obligatorio para boletos')
            if not self.numero_boleto:
                errors['numero_boleto'] = _('Número de boleto obligatorio')
            if not self.itinerario:
                errors['itinerario'] = _('Itinerario obligatorio para boletos')
        
        if errors:
            raise ValidationError(errors)


class NotaDebitoVenezuela(models.Model):
    """
    Nota de Débito por IVA sobre ganancia cambiaria.
    Según normativa venezolana, las ganancias cambiarias incrementan la base imponible.
    """
    id_nota_debito = models.AutoField(primary_key=True, verbose_name=_("ID Nota Débito"))
    factura_origen = models.ForeignKey(
        FacturaVenezuela,
        on_delete=models.PROTECT,
        related_name='notas_debito',
        verbose_name=_("Factura Origen")
    )
    numero_nota_debito = models.CharField(
        _("Número Nota Débito"),
        max_length=50,
        unique=True,
        help_text=_("Número correlativo de la nota de débito")
    )
    fecha_emision = models.DateTimeField(_("Fecha Emisión"), default=timezone.now)
    
    # Diferencial cambiario que origina la nota
    ganancia_cambiaria_bsd = models.DecimalField(
        _("Ganancia Cambiaria BSD"),
        max_digits=15,
        decimal_places=2,
        help_text=_("Monto de la ganancia cambiaria en bolívares")
    )
    
    # IVA calculado sobre la ganancia
    monto_iva_bsd = models.DecimalField(
        _("IVA 16% BSD"),
        max_digits=15,
        decimal_places=2,
        help_text=_("IVA sobre la ganancia cambiaria")
    )
    
    # Tasas involucradas
    tasa_factura = models.DecimalField(
        _("Tasa Factura"),
        max_digits=12,
        decimal_places=4,
        help_text=_("Tasa BCV al momento de la factura")
    )
    
    tasa_pago = models.DecimalField(
        _("Tasa Pago"),
        max_digits=12,
        decimal_places=4,
        help_text=_("Tasa BCV al momento del pago")
    )
    
    # Referencia al pago que generó el diferencial
    referencia_pago = models.CharField(
        _("Referencia Pago"),
        max_length=100,
        blank=True,
        help_text=_("Referencia del pago que originó la ganancia")
    )
    
    # Estado
    class EstadoNotaDebito(models.TextChoices):
        EMITIDA = 'EMI', _('Emitida')
        COBRADA = 'COB', _('Cobrada')
        ANULADA = 'ANU', _('Anulada')
    
    estado = models.CharField(
        _("Estado"),
        max_length=3,
        choices=EstadoNotaDebito.choices,
        default=EstadoNotaDebito.EMITIDA
    )
    
    observaciones = models.TextField(_("Observaciones"), blank=True, null=True)
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("Nota de Débito Venezuela")
        verbose_name_plural = _("Notas de Débito Venezuela")
        ordering = ['-fecha_emision']
    
    def __str__(self):
        return f"ND {self.numero_nota_debito} - Factura {self.factura_origen.numero_factura}"
    
    def save(self, *args, **kwargs):
        # Generar número automático si no existe
        if not self.numero_nota_debito:
            ultimo = NotaDebitoVenezuela.objects.order_by('-id_nota_debito').first()
            siguiente = (ultimo.id_nota_debito + 1) if ultimo else 1
            self.numero_nota_debito = f"ND-{self.fecha_emision.year}-{siguiente:06d}"
        super().save(*args, **kwargs)


# Modelo para documentación de exportación
class DocumentoExportacion(models.Model):
    """
    Documentos de soporte para facturas de exportación de servicios.
    Requerido para sustentar alícuota 0% en turismo receptivo.
    """
    factura = models.ForeignKey(
        FacturaVenezuela, 
        on_delete=models.CASCADE, 
        related_name='documentos_exportacion'
    )
    
    tipo_documento = models.CharField(
        _("Tipo Documento"), 
        max_length=20,
        choices=[
            ('PASAPORTE', _('Pasaporte')),
            ('COMPROBANTE_PAGO', _('Comprobante Pago Internacional')),
            ('OTRO', _('Otro'))
        ]
    )
    
    numero_documento = models.CharField(_("Número Documento"), max_length=100)
    archivo = models.FileField(_("Archivo"), upload_to='documentos_exportacion/%Y/%m/')
    fecha_subida = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = _("Documento Exportación")
        verbose_name_plural = _("Documentos Exportación")
    
    def __str__(self):
        return f"{self.tipo_documento} - {self.numero_documento}"
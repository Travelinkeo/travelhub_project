# core/models/retenciones_islr.py
"""
Modelo para gestión de Retenciones de ISLR
Cumple con Decreto 1.808 y normativa SENIAT
"""
from decimal import Decimal
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from core.models import FacturaConsolidada
from personas.models import Cliente


class RetencionISLR(models.Model):
    """Comprobante de Retención de ISLR recibido"""
    
    class TipoOperacion(models.TextChoices):
        HONORARIOS_PROFESIONALES = 'HP', _('Honorarios Profesionales')
        SERVICIOS_NO_MERCANTILES = 'SNM', _('Servicios No Mercantiles')
        COMISIONES_MERCANTILES = 'CM', _('Comisiones Mercantiles')
        OTROS = 'OT', _('Otros')
    
    class Estado(models.TextChoices):
        PENDIENTE = 'PEN', _('Pendiente')
        APLICADA = 'APL', _('Aplicada en Declaración')
        ANULADA = 'ANU', _('Anulada')
    
    # Identificación
    id_retencion = models.AutoField(primary_key=True, verbose_name=_("ID Retención"))
    numero_comprobante = models.CharField(_("Número de Comprobante"), max_length=50, unique=True,
                                         help_text=_("Número del comprobante de retención"))
    
    # Relaciones
    factura = models.ForeignKey(FacturaConsolidada, on_delete=models.PROTECT,
                               related_name='retenciones_islr',
                               verbose_name=_("Factura"))
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT,
                               verbose_name=_("Cliente (Agente de Retención)"))
    
    # Fechas
    fecha_emision = models.DateField(_("Fecha de Emisión"), default=timezone.now)
    fecha_operacion = models.DateField(_("Fecha de Operación"),
                                      help_text=_("Fecha de la factura retenida"))
    periodo_fiscal = models.CharField(_("Período Fiscal"), max_length=7,
                                     help_text=_("Formato: YYYY-MM"))
    
    # Tipo de operación
    tipo_operacion = models.CharField(_("Tipo de Operación"), max_length=3,
                                     choices=TipoOperacion.choices,
                                     default=TipoOperacion.COMISIONES_MERCANTILES)
    codigo_concepto = models.CharField(_("Código Concepto SENIAT"), max_length=10,
                                      blank=True,
                                      help_text=_("Ej: 03-04 para comisiones"))
    
    # Montos
    base_imponible = models.DecimalField(_("Base Imponible"), max_digits=12, decimal_places=2,
                                        help_text=_("Monto sobre el cual se calcula la retención"))
    porcentaje_retencion = models.DecimalField(_("Porcentaje de Retención"), max_digits=5, decimal_places=2,
                                              default=Decimal('5.00'),
                                              help_text=_("Porcentaje aplicado (ej: 5.00)"))
    monto_retenido = models.DecimalField(_("Monto Retenido"), max_digits=12, decimal_places=2,
                                        help_text=_("Monto efectivamente retenido"))
    
    # Estado
    estado = models.CharField(_("Estado"), max_length=3, choices=Estado.choices,
                            default=Estado.PENDIENTE)
    
    # Archivo
    archivo_comprobante = models.FileField(_("Archivo Comprobante"),
                                          upload_to='retenciones_islr/%Y/%m/',
                                          blank=True, null=True,
                                          help_text=_("PDF del comprobante de retención"))
    
    # Notas
    observaciones = models.TextField(_("Observaciones"), blank=True)
    
    # Auditoría
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("Retención ISLR")
        verbose_name_plural = _("Retenciones ISLR")
        ordering = ['-fecha_emision', '-numero_comprobante']
        indexes = [
            models.Index(fields=['periodo_fiscal']),
            models.Index(fields=['estado']),
            models.Index(fields=['cliente', 'fecha_emision']),
        ]
    
    def __str__(self):
        return f"{self.numero_comprobante} - {self.cliente} - ${self.monto_retenido}"
    
    def save(self, *args, **kwargs):
        # Calcular monto retenido si no está definido
        if not self.monto_retenido and self.base_imponible and self.porcentaje_retencion:
            self.monto_retenido = self.base_imponible * (self.porcentaje_retencion / 100)
        
        # Generar período fiscal si no está definido
        if not self.periodo_fiscal:
            self.periodo_fiscal = self.fecha_emision.strftime('%Y-%m')
        
        super().save(*args, **kwargs)

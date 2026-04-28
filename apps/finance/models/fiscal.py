from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.bookings.models import Venta

class FacturaFiscal(models.Model):
    """
    Representa el documento fiscal oficial ante los entes gubernamentales (SENIAT, DIAN, etc.).
    Mantiene la integridad de la firma digital y el XML enviado.
    """
    class EstadoFiscal(models.TextChoices):
        PENDIENTE = 'PEN', _('Pendiente de Envío')
        EN_PROCESO = 'PRO', _('En Procesamiento / Firmado')
        APROBADA = 'APR', _('Aprobada / Autorizada')
        RECHAZADA = 'REC', _('Rechazada por Error Fiscal')

    venta = models.OneToOneField(Venta, on_delete=models.CASCADE, related_name='factura_fiscal', verbose_name=_("Venta Asociada"))
    
    # Datos fiscales oficiales
    numero_factura = models.CharField(_("Número de Factura Fiscal"), max_length=50, blank=True)
    numero_control = models.CharField(_("Número de Control"), max_length=50, blank=True)
    
    # Firma y XML
    cadena_firma_digital = models.TextField(_("Cadena de Firma Digital"), blank=True)
    xml_generado = models.TextField(_("XML Fiscal Generado"), blank=True)
    
    estado_fiscal = models.CharField(_("Estado Fiscal"), max_length=3, choices=EstadoFiscal.choices, default=EstadoFiscal.PENDIENTE)
    
    # Auditoría de Errores
    ultimo_mensaje_error = models.TextField(_("Último Error"), blank=True, null=True)
    fecha_emision_fiscal = models.DateTimeField(_("Fecha Emisión Fiscal"), null=True, blank=True)
    
    class Meta:
        verbose_name = _("Factura Fiscal Electrónica")
        verbose_name_plural = _("Facturas Fiscales Electrónicas")

    def __str__(self):
        return f"Fiscal {self.numero_factura or 'PENDIENTE'} - Venta {self.venta.localizador}"

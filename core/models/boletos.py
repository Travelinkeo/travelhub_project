# Archivo: core/models/boletos.py
import logging

from django.db import models
from django.utils.translation import gettext_lazy as _

from core.validators import antivirus_hook, validate_file_extension, validate_file_size

from .ventas import Venta

logger = logging.getLogger(__name__)

class BoletoImportado(models.Model):
    id_boleto_importado = models.AutoField(primary_key=True, verbose_name=_("ID Boleto Importado"))
    archivo_boleto = models.FileField(
        _("Archivo del Boleto (.pdf, .txt, .eml)"),
        upload_to='boletos_importados/%Y/%m/',
        help_text=_("Suba el archivo del boleto en formato PDF, TXT o EML (máx 5MB)."),
        validators=[validate_file_size, validate_file_extension, antivirus_hook],
        storage=lambda: __import__('core.storage', fromlist=['PDFCloudinaryStorage']).PDFCloudinaryStorage(),
        blank=True, null=True
    )
    fecha_subida = models.DateTimeField(_("Fecha de Subida"), auto_now_add=True)
    
    class FormatoDetectado(models.TextChoices):
        PDF_KIU = 'PDF_KIU', _('PDF (KIU)')
        PDF_SABRE = 'PDF_SAB', _('PDF (Sabre)')
        PDF_AMADEUS = 'PDF_AMA', _('PDF (Amadeus)')
        TXT_KIU = 'TXT_KIU', _('TXT (KIU)')
        TXT_SABRE = 'TXT_SAB', _('TXT (Sabre)')
        TXT_AMADEUS = 'TXT_AMA', _('TXT (Amadeus)')
        EML_KIU = 'EML_KIU', _('EML (KIU)') 
        EML_GENERAL = 'EML_GEN', _('EML (General)')
        OTRO = 'OTR', _('Otro/Desconocido')
        ERROR_FORMATO = 'ERR', _('Error de Formato')

    formato_detectado = models.CharField(
        _("Formato Detectado"),
        max_length=20,  # Aumentado de 10 a 20
        choices=FormatoDetectado.choices,
        default=FormatoDetectado.OTRO,
        blank=True
    )
    
    datos_parseados = models.JSONField(_("Datos Parseados"), blank=True, null=True, help_text=_("Información extraída del boleto en formato JSON."))
    
    class EstadoParseo(models.TextChoices):
        PENDIENTE = 'PEN', _('Pendiente de Parseo')
        EN_PROCESO = 'PRO', _('En Proceso')
        COMPLETADO = 'COM', _('Parseo Completado')
        ERROR_PARSEO = 'ERR', _('Error en Parseo')
        NO_APLICA = 'NAP', _('No Aplica Parseo')

    estado_parseo = models.CharField(
        _("Estado del Parseo"),
        max_length=3,
        choices=EstadoParseo.choices,
        default=EstadoParseo.PENDIENTE,
    )
    log_parseo = models.TextField(_("Log del Parseo"), blank=True, null=True)
    
    numero_boleto = models.CharField(_("Número de Boleto"), max_length=50, blank=True, null=True)
    nombre_pasajero_completo = models.CharField(_("Nombre Completo Pasajero (Original)"), max_length=150, blank=True, null=True)
    nombre_pasajero_procesado = models.CharField(_("Nombre Pasajero (Procesado)"), max_length=150, blank=True, null=True)
    ruta_vuelo = models.TextField(_("Ruta del Vuelo (Itinerario)"), blank=True, null=True) 
    fecha_emision_boleto = models.DateField(_("Fecha de Emisión del Boleto"), blank=True, null=True)
    aerolinea_emisora = models.CharField(_("Aerolínea Emisora"), max_length=100, blank=True, null=True)
    direccion_aerolinea = models.TextField(_("Dirección Aerolínea"), blank=True, null=True)
    agente_emisor = models.CharField(_("Agente Emisor"), max_length=100, blank=True, null=True)
    foid_pasajero = models.CharField(_("FOID/D.Identidad Pasajero"), max_length=50, blank=True, null=True)
    localizador_pnr = models.CharField(_("Localizador (PNR)"), max_length=20, blank=True, null=True)
    tarifa_base = models.DecimalField(_("Tarifa Base"), max_digits=10, decimal_places=2, blank=True, null=True)
    impuestos_descripcion = models.TextField(_("Descripción Impuestos"), blank=True, null=True)
    impuestos_total_calculado = models.DecimalField(_("Total Impuestos (Calculado)"), max_digits=10, decimal_places=2, blank=True, null=True)
    total_boleto = models.DecimalField(_("Total del Boleto"), max_digits=10, decimal_places=2, blank=True, null=True)
    exchange_monto = models.DecimalField(_("Exchange"), max_digits=10, decimal_places=2, blank=True, null=True, help_text=_("Monto de exchange o diferencial de cambio asociado al boleto."))
    void_monto = models.DecimalField(_("Void / Penalidad"), max_digits=10, decimal_places=2, blank=True, null=True, help_text=_("Monto asociado a VOID (penalidad / reembolso negativo)."))
    fee_servicio = models.DecimalField(_("Fee de Servicio"), max_digits=10, decimal_places=2, blank=True, null=True, help_text=_("Fee cobrado por la agencia por gestión del boleto."))
    igtf_monto = models.DecimalField(_("IGTF"), max_digits=10, decimal_places=2, blank=True, null=True, help_text=_("Impuesto a las Grandes Transacciones Financieras u otras retenciones locales."))
    comision_agencia = models.DecimalField(_("Comisión Agencia"), max_digits=10, decimal_places=2, blank=True, null=True, help_text=_("Comisión propia de la agencia respecto al boleto."))
    
    venta_asociada = models.OneToOneField(Venta, on_delete=models.SET_NULL, blank=True, null=True, related_name='boleto_importado', verbose_name=_("Venta/Reserva Asociada"))
    archivo_pdf_generado = models.FileField(
        _("PDF Unificado Generado"),
        upload_to='boletos_generados/%Y/%m/',
        storage=lambda: __import__('core.storage', fromlist=['PDFCloudinaryStorage']).PDFCloudinaryStorage(),
        blank=True, null=True,
        help_text=_("El archivo PDF del boleto unificado, generado automáticamente.")
    )

    class Meta:
        verbose_name = _("Boleto Importado")
        verbose_name_plural = _("Boletos Importados")
        ordering = ['-fecha_subida']

    def __str__(self):
        return f"Boleto {self.id_boleto_importado} ({self.archivo_boleto.name if self.archivo_boleto else 'N/A'})"

    def parsear(self):
        """Punto de entrada manual para el parseo (proxy al servicio)."""
        from core.services.parsing import procesar_boleto_importado
        procesar_boleto_importado(self)

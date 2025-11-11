"""
Modelo para historial de cambios en boletos
"""
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model

User = get_user_model()


class HistorialCambioBoleto(models.Model):
    """Registra cada cambio realizado en un boleto"""
    
    class TipoCambio(models.TextChoices):
        CAMBIO_FECHA = 'CF', _('Cambio de Fecha')
        CAMBIO_PASAJERO = 'CP', _('Cambio de Pasajero')
        REEMISION = 'RE', _('Reemisión')
        CANCELACION = 'CA', _('Cancelación')
        CORRECCION = 'CO', _('Corrección')
        OTRO = 'OT', _('Otro')
    
    id_historial = models.AutoField(primary_key=True)
    boleto = models.ForeignKey(
        'core.BoletoImportado',
        on_delete=models.CASCADE,
        related_name='historial_cambios'
    )
    tipo_cambio = models.CharField(max_length=2, choices=TipoCambio.choices)
    descripcion = models.TextField(_("Descripción del Cambio"))
    
    # Datos anteriores (JSON)
    datos_anteriores = models.JSONField(blank=True, null=True)
    datos_nuevos = models.JSONField(blank=True, null=True)
    
    # Costos asociados
    costo_cambio = models.DecimalField(
        max_digits=10, decimal_places=2,
        blank=True, null=True,
        help_text=_("Costo cobrado por el cambio")
    )
    penalidad = models.DecimalField(
        max_digits=10, decimal_places=2,
        blank=True, null=True,
        help_text=_("Penalidad aplicada")
    )
    
    # Auditoría
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    fecha_cambio = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = _("Historial de Cambio de Boleto")
        verbose_name_plural = _("Historial de Cambios de Boletos")
        ordering = ['-fecha_cambio']
    
    def __str__(self):
        return f"{self.get_tipo_cambio_display()} - {self.boleto.numero_boleto} - {self.fecha_cambio}"

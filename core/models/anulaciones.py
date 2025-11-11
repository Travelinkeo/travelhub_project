"""
Modelo para gestión de anulaciones y reembolsos
"""
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
from decimal import Decimal

User = get_user_model()


class AnulacionBoleto(models.Model):
    """Gestiona anulaciones y reembolsos de boletos"""
    
    class EstadoAnulacion(models.TextChoices):
        SOLICITADA = 'SOL', _('Solicitada')
        EN_PROCESO = 'PRO', _('En Proceso')
        APROBADA = 'APR', _('Aprobada')
        RECHAZADA = 'REC', _('Rechazada')
        REEMBOLSADA = 'REE', _('Reembolsada')
    
    class TipoAnulacion(models.TextChoices):
        VOLUNTARIA = 'VOL', _('Voluntaria')
        INVOLUNTARIA = 'INV', _('Involuntaria')
        CAMBIO_ITINERARIO = 'CAM', _('Cambio de Itinerario')
    
    id_anulacion = models.AutoField(primary_key=True)
    boleto = models.ForeignKey(
        'core.BoletoImportado',
        on_delete=models.CASCADE,
        related_name='anulaciones'
    )
    
    tipo_anulacion = models.CharField(max_length=3, choices=TipoAnulacion.choices)
    estado = models.CharField(
        max_length=3,
        choices=EstadoAnulacion.choices,
        default=EstadoAnulacion.SOLICITADA
    )
    
    motivo = models.TextField(_("Motivo de Anulación"))
    
    # Montos
    monto_original = models.DecimalField(max_digits=10, decimal_places=2)
    penalidad_aerolinea = models.DecimalField(
        max_digits=10, decimal_places=2,
        default=Decimal('0.00')
    )
    fee_agencia = models.DecimalField(
        max_digits=10, decimal_places=2,
        default=Decimal('0.00')
    )
    monto_reembolso = models.DecimalField(
        max_digits=10, decimal_places=2,
        editable=False
    )
    
    # Tracking
    fecha_solicitud = models.DateTimeField(auto_now_add=True)
    fecha_aprobacion = models.DateTimeField(blank=True, null=True)
    fecha_reembolso = models.DateTimeField(blank=True, null=True)
    
    # Auditoría
    solicitado_por = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, related_name='anulaciones_solicitadas'
    )
    aprobado_por = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='anulaciones_aprobadas'
    )
    
    notas = models.TextField(blank=True)
    
    class Meta:
        verbose_name = _("Anulación de Boleto")
        verbose_name_plural = _("Anulaciones de Boletos")
        ordering = ['-fecha_solicitud']
    
    def save(self, *args, **kwargs):
        # Calcular monto de reembolso
        self.monto_reembolso = self.monto_original - self.penalidad_aerolinea - self.fee_agencia
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Anulación {self.id_anulacion} - {self.boleto.numero_boleto}"

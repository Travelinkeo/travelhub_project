from django.db import models
import uuid

class TaxRefundOpportunity(models.Model):
    """
    Oportunidad financiera detectada automáticamente por el Escáner Silencioso.
    Representa impuestos recuperables de un vuelo internacional.
    """
    class Estado(models.TextChoices):
        ELEGIBLE = 'ELE', 'Elegible (Dinero en la mesa)'
        TRAMITANDO = 'TRA', 'En Trámite (Global Blue / Partner)'
        COMPLETADO = 'COM', 'Completado (Dinero Recuperado)'
        RECHAZADO = 'REC', 'Rechazado'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Use string references to avoid circular imports
    boleto = models.OneToOneField('bookings.BoletoImportado', on_delete=models.CASCADE, related_name='tax_refund_oo')
    agencia = models.ForeignKey('core.Agencia', on_delete=models.CASCADE, related_name='tax_refund_oo')
    
    # Cálculos Financieros
    monto_estimado = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    monto_recuperado = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    
    estado = models.CharField(max_length=3, choices=Estado.choices, default=Estado.ELEGIBLE)
    tracking_code_proveedor = models.CharField(max_length=100, blank=True, null=True, help_text="Ej. Global Blue Tracking ID")
    
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Refund {self.id} - PNR: {self.boleto.localizador_pnr}"

import uuid
from django.db import models
from django.utils import timezone
from datetime import timedelta
from apps.bookings.models import Venta

class LinkDePago(models.Model):
    """
    Contrato de seguridad para pagos externos (B2C).
    Genera una URL única e inexpugnable para que el cliente pague su itinerario.
    """
    class EstadoPago(models.TextChoices):
        PENDIENTE = 'PEN', 'Pendiente'
        EN_REVISION = 'REV', 'En Revisión (Zelle/Transf)'
        PAGADO = 'PAG', 'Pagado Exitosamente'
        EXPIRADO = 'EXP', 'Expirado'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    venta = models.OneToOneField(Venta, on_delete=models.CASCADE, related_name='link_pago')
    
    monto_total = models.DecimalField(max_digits=12, decimal_places=2)
    moneda = models.CharField(max_length=3, default='USD')
    
    estado = models.CharField(max_length=3, choices=EstadoPago.choices, default=EstadoPago.PENDIENTE)
    
    # Tracking de Zelle/Transferencias manuales
    referencia_pago = models.CharField(max_length=100, blank=True, null=True)
    comprobante_imagen = models.ImageField(upload_to='comprobantes_pago/', blank=True, null=True)
    
    creado_en = models.DateTimeField(auto_now_add=True)
    expira_en = models.DateTimeField()

    def save(self, *args, **kwargs):
        if not self.expira_en:
            # Los links mágicos expiran en 24 horas por defecto para crear urgencia
            self.expira_en = timezone.now() + timedelta(hours=24)
        super().save(*args, **kwargs)

    @property
    def esta_activo(self):
        return self.estado == self.EstadoPago.PENDIENTE and timezone.now() < self.expira_en

    def __str__(self):
        return f"Link {self.id} - Venta {self.venta.localizador} ({self.estado})"

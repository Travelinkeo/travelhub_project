from django.db import models
from django.utils.translation import gettext_lazy as _
from decimal import Decimal
from core.managers import TenantManager
from core.models.agencia import Agencia

class ProductoTerrestre(models.Model):
    class TipoServicio(models.TextChoices):
        HOTEL = 'HOTEL', _('Hotel / Alojamiento')
        TOUR = 'TOUR', _('Tour / Excursión')
        TRASLADO = 'TRANS', _('Traslado')
        PAQUETE = 'PACK', _('Paquete Dinámico')
        SEGURO = 'INS', _('Seguro de Viaje')

    agencia = models.ForeignKey('core.Agencia', on_delete=models.CASCADE, related_name='productos_terrestres', null=True, blank=True)
    tipo_servicio = models.CharField(_("Tipo de Servicio"), max_length=10, choices=TipoServicio.choices, default=TipoServicio.HOTEL)
    nombre = models.CharField(_("Nombre Comercial"), max_length=255)
    destino = models.CharField(_("Destino / Ubicación"), max_length=255, help_text=_("Ej. Madrid, España"))
    descripcion_publica = models.TextField(_("Descripción (Pública)"), blank=True, null=True, help_text=_("Lo que verá el cliente en la cotización"))
    
    costo_neto = models.DecimalField(_("Costo Neto (Proveedor)"), max_digits=12, decimal_places=2)
    markup_porcentaje = models.DecimalField(_("Markup (Ganancia %)"), max_digits=5, decimal_places=2, default=Decimal('20.00'))
    precio_venta_calculado = models.DecimalField(_("Precio Venta"), max_digits=12, decimal_places=2, editable=False)
    
    imagen_principal = models.ImageField(_("Foto Principal"), upload_to='productos_terrestres/%Y/%m/', blank=True, null=True)
    activo = models.BooleanField(_("Activo"), default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    objects = TenantManager()
    all_objects = models.Manager()

    class Meta:
        verbose_name = _("Producto Terrestre")
        verbose_name_plural = _("Productos Terrestres")
        ordering = ['-fecha_creacion']

    def save(self, *args, **kwargs):
        # Calcular el precio de venta antes de guardar
        self.precio_venta_calculado = self.costo_neto + (self.costo_neto * (self.markup_porcentaje / Decimal('100.00')))
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.nombre} ({self.get_tipo_servicio_display()}) - {self.destino}"

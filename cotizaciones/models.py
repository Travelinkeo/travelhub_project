"""Modelos de Cotizaciones.

Estos modelos se separan en su propia app `cotizaciones` para romper dependencias
circulares y permitir una carga controlada.
"""
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from decimal import Decimal

from personas.models import Cliente
from core.models_catalogos import Moneda, ProductoServicio

class Cotizacion(models.Model):
    id_cotizacion = models.AutoField(primary_key=True, verbose_name=_("ID Cotización"))
    numero_cotizacion = models.CharField(_("Número de Cotización"), max_length=50, unique=True, blank=True)
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, verbose_name=_("Cliente"))
    fecha_emision = models.DateField(_("Fecha de Emisión"), default=timezone.now)
    fecha_vencimiento = models.DateField(_("Fecha de Vencimiento"), blank=True, null=True)
    moneda = models.ForeignKey(Moneda, on_delete=models.PROTECT, verbose_name=_("Moneda"), related_name='cotizaciones_cotizaciones')
    total_cotizado = models.DecimalField(_("Total Cotizado"), max_digits=12, decimal_places=2, default=0, editable=False)
    class EstadoCotizacion(models.TextChoices):
        BORRADOR = 'BOR', _('Borrador')
        ENVIADA = 'ENV', _('Enviada al Cliente')
        ACEPTADA = 'ACE', _('Aceptada')
        RECHAZADA = 'REC', _('Rechazada')
        VENCIDA = 'VEN', _('Vencida')
    estado = models.CharField(_("Estado"), max_length=3, choices=EstadoCotizacion.choices, default=EstadoCotizacion.BORRADOR)
    notas = models.TextField(_("Notas"), blank=True, null=True)
    class Meta:
        verbose_name = _("Cotización")
        verbose_name_plural = _("Cotizaciones")
        ordering = ['-fecha_emision']
    def __str__(self):
        return self.numero_cotizacion or f"COT-{self.id_cotizacion}"
    def save(self, *args, **kwargs):
        if not self.numero_cotizacion:
            self.numero_cotizacion = f"COT-{self.fecha_emision.strftime('%Y%m%d')}-{Cotizacion.objects.count() + 1:04d}"
        super().save(*args, **kwargs)
    def calcular_totales_desde_items(self):
        total = self.items_cotizacion.aggregate(total=models.Sum('subtotal_item'))['total'] or Decimal('0.00')
        self.total_cotizado = total
        self.save(update_fields=['total_cotizado'])

class ItemCotizacion(models.Model):
    id_item_cotizacion = models.AutoField(primary_key=True, verbose_name=_("ID Item Cotización"))
    cotizacion = models.ForeignKey(Cotizacion, related_name='items_cotizacion', on_delete=models.CASCADE, verbose_name=_("Cotización"))
    producto_servicio = models.ForeignKey(ProductoServicio, on_delete=models.PROTECT, verbose_name=_("Producto/Servicio"), related_name='cotizaciones_items_cotizacion')
    descripcion_personalizada = models.CharField(_("Descripción Personalizada"), max_length=500, blank=True, null=True)
    cantidad = models.DecimalField(_("Cantidad"), max_digits=10, decimal_places=2, default=1)
    precio_unitario = models.DecimalField(_("Precio Unitario"), max_digits=12, decimal_places=2)
    subtotal_item = models.DecimalField(_("Subtotal Item"), max_digits=12, decimal_places=2, editable=False)
    class Meta:
        verbose_name = _("Item de Cotización")
        verbose_name_plural = _("Items de Cotización")
    def __str__(self):
        return f"{self.cantidad} x {self.producto_servicio.nombre}"
    def save(self, *args, **kwargs):
        self.subtotal_item = self.precio_unitario * self.cantidad
        super().save(*args, **kwargs)

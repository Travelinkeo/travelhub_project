from __future__ import annotations

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from core.models.personas import Cliente  # Import Cliente from its new location
from core.models_catalogos import Moneda, ProductoServicio


class Cotizacion(models.Model):
    id_cotizacion = models.AutoField(primary_key=True, verbose_name=_('ID Cotización'))
    numero_cotizacion = models.CharField(_('Número de Cotización'), max_length=20, unique=True, blank=True, help_text=_('Generado automáticamente o manual.'))
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, verbose_name=_('Cliente'))
    fecha_emision = models.DateTimeField(_('Fecha de Emisión'), default=timezone.now)
    fecha_validez = models.DateField(_('Válida Hasta'), blank=True, null=True)
    descripcion_general = models.TextField(_('Descripción General del Viaje/Servicio'), blank=True, null=True)
    moneda = models.ForeignKey(Moneda, on_delete=models.PROTECT, verbose_name=_('Moneda'), related_name='core_cotizaciones')
    subtotal = models.DecimalField(_('Subtotal'), max_digits=12, decimal_places=2, default=0)
    impuestos = models.DecimalField(_('Impuestos'), max_digits=12, decimal_places=2, default=0)
    total_cotizado = models.DecimalField(_('Total Cotizado'), max_digits=12, decimal_places=2, default=0)
    class EstadoCotizacion(models.TextChoices):
        BORRADOR = 'BOR', _('Borrador')
        ENVIADA = 'ENV', _('Enviada al Cliente')
        ACEPTADA = 'ACE', _('Aceptada por el Cliente')
        RECHAZADA = 'REC', _('Rechazada por el Cliente')
        VENCIDA = 'VEN', _('Vencida')
        CONVERTIDA_A_VENTA = 'CNV', _('Convertida a Venta/Reserva')
    estado = models.CharField(_('Estado de la Cotización'), max_length=3, choices=EstadoCotizacion.choices, default=EstadoCotizacion.BORRADOR)
    notas_internas = models.TextField(_('Notas Internas'), blank=True, null=True)
    condiciones_comerciales = models.TextField(_('Condiciones Comerciales'), blank=True, null=True, help_text=_('Ej. políticas de cancelación, pagos, etc.'))
    class Meta:
        verbose_name = _('Cotización')
        verbose_name_plural = _('Cotizaciones')
        ordering = ['-fecha_emision']
    def __str__(self):  # pragma: no cover
        return f"Cotización {self.numero_cotizacion or self.id_cotizacion} para {self.cliente}"
    def save(self, *args, **kwargs):  # pragma: no cover - lógica igual
        if not self.numero_cotizacion:
            self.numero_cotizacion = f"COT-{timezone.now().strftime('%Y%m%d')}-{Cotizacion.objects.count() + 1:04d}"
        self.total_cotizado = (self.subtotal or 0) + (self.impuestos or 0)
        super().save(*args, **kwargs)


class ItemCotizacion(models.Model):
    id_item_cotizacion = models.AutoField(primary_key=True, verbose_name=_('ID Item Cotización'))
    cotizacion = models.ForeignKey(Cotizacion, related_name='items_cotizacion', on_delete=models.CASCADE, verbose_name=_('Cotización'))
    producto_servicio = models.ForeignKey(ProductoServicio, on_delete=models.PROTECT, verbose_name=_('Producto/Servicio'), related_name='core_items_cotizacion')
    descripcion_personalizada = models.CharField(_('Descripción Personalizada'), max_length=500, blank=True, null=True, help_text=_('Si se desea una descripción diferente a la del catálogo.'))
    cantidad = models.PositiveIntegerField(_('Cantidad'), default=1)
    precio_unitario = models.DecimalField(_('Precio Unitario'), max_digits=12, decimal_places=2)
    impuestos_item = models.DecimalField(_('Impuestos por Item'), max_digits=12, decimal_places=2, default=0)
    subtotal_item = models.DecimalField(_('Subtotal Item'), max_digits=12, decimal_places=2, editable=False)
    total_item = models.DecimalField(_('Total Item'), max_digits=12, decimal_places=2, editable=False)
    class Meta:
        verbose_name = _('Item de Cotización')
        verbose_name_plural = _('Items de Cotización')
        ordering = ['id_item_cotizacion']
    def __str__(self):  # pragma: no cover
        return f"{self.cantidad} x {self.producto_servicio.nombre} en {self.cotizacion.numero_cotizacion}"
    def save(self, *args, **kwargs):  # pragma: no cover
        self.subtotal_item = self.precio_unitario * self.cantidad
        self.total_item = self.subtotal_item + (self.impuestos_item * self.cantidad)
        super().save(*args, **kwargs)

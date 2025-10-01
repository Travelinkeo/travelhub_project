# Archivo: core/models/facturacion.py
import logging
from decimal import Decimal

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from personas.models import Cliente
from core.models_catalogos import Moneda

from .contabilidad import AsientoContable

logger = logging.getLogger(__name__)


class Factura(models.Model):
    id_factura = models.AutoField(primary_key=True, verbose_name=_("ID Factura"))
    numero_factura = models.CharField(_("Número de Factura"), max_length=50, unique=True, blank=True, help_text=_("Puede ser un correlativo fiscal o interno."))

    venta_asociada = models.ForeignKey('Venta', on_delete=models.SET_NULL, blank=True, null=True, related_name='facturas', verbose_name=_("Venta Asociada"))
    cliente = models.ForeignKey('personas.Cliente', on_delete=models.PROTECT, verbose_name=_("Cliente"), blank=True, null=True)

    fecha_emision = models.DateField(_("Fecha de Emisión"), default=timezone.now)
    fecha_vencimiento = models.DateField(_("Fecha de Vencimiento"), blank=True, null=True)
    moneda = models.ForeignKey(Moneda, on_delete=models.PROTECT, verbose_name=_("Moneda"))
    subtotal = models.DecimalField(_("Subtotal"), max_digits=12, decimal_places=2, default=0)
    monto_impuestos = models.DecimalField(_("Monto Impuestos"), max_digits=12, decimal_places=2, default=0)
    monto_total = models.DecimalField(_("Monto Total"), max_digits=12, decimal_places=2, editable=False, default=0)
    saldo_pendiente = models.DecimalField(_("Saldo Pendiente"), max_digits=12, decimal_places=2, editable=False, default=0)
    
    class EstadoFactura(models.TextChoices):
        BORRADOR = 'BOR', _('Borrador')
        EMITIDA = 'EMI', _('Emitida (Pendiente de Pago)')
        PARCIAL = 'PAR', _('Pagada Parcialmente')
        PAGADA = 'PAG', _('Pagada Totalmente')
        VENCIDA = 'VEN', _('Vencida')
        ANULADA = 'ANU', _('Anulada')
    
    estado = models.CharField(_("Estado de la Factura"), max_length=3, choices=EstadoFactura.choices, default=EstadoFactura.BORRADOR)
    notas = models.TextField(_("Notas de la Factura"), blank=True, null=True)
    asiento_contable_factura = models.ForeignKey(AsientoContable, related_name='facturas_asociadas', on_delete=models.SET_NULL, blank=True, null=True, verbose_name=_("Asiento Contable de Factura"))
    archivo_pdf = models.FileField(_("Archivo PDF"), upload_to='facturas/%Y/%m/', blank=True, null=True)

    class Meta:
        verbose_name = _("Factura de Cliente")
        verbose_name_plural = _("Facturas de Clientes")
        ordering = ['-fecha_emision', '-numero_factura']

    def __str__(self):
        return self.numero_factura or f"FACT-{self.id_factura}"

    def save(self, *args, **kwargs):
        es_creacion = self.pk is None
        if not self.numero_factura:
            consecutivo = Factura.objects.count() + 1 if es_creacion else self.pk
            self.numero_factura = f"F-{self.fecha_emision.strftime('%Y%m%d')}-{consecutivo:04d}"
        
        self.monto_total = (self.subtotal or 0) + (self.monto_impuestos or 0)
        
        if es_creacion or self.saldo_pendiente is None:
            self.saldo_pendiente = self.monto_total
        else:
            if self.saldo_pendiente > self.monto_total:
                self.saldo_pendiente = self.monto_total
        
        if self.estado in {self.EstadoFactura.BORRADOR, self.EstadoFactura.EMITIDA, self.EstadoFactura.PARCIAL, self.EstadoFactura.PAGADA}:
            if self.saldo_pendiente <= 0 and self.monto_total > 0:
                self.estado = self.EstadoFactura.PAGADA
            elif 0 < self.saldo_pendiente < self.monto_total:
                self.estado = self.EstadoFactura.PARCIAL
            elif self.estado == self.EstadoFactura.BORRADOR and self.monto_total > 0:
                self.estado = self.EstadoFactura.EMITIDA
        
        super().save(*args, **kwargs)

class ItemFactura(models.Model):
    id_item_factura = models.AutoField(primary_key=True, verbose_name=_("ID Item Factura"))
    factura = models.ForeignKey(Factura, related_name='items_factura', on_delete=models.CASCADE, verbose_name=_("Factura"))
    descripcion = models.CharField(_("Descripción del Item"), max_length=500)
    cantidad = models.DecimalField(_("Cantidad"), max_digits=10, decimal_places=2, default=1)
    precio_unitario = models.DecimalField(_("Precio Unitario"), max_digits=12, decimal_places=2)
    subtotal_item = models.DecimalField(_("Subtotal Item"), max_digits=12, decimal_places=2, editable=False)

    class Meta:
        verbose_name = _("Item de Factura")
        verbose_name_plural = _("Items de Factura")

    def __str__(self):
        return f"{self.cantidad} x {self.descripcion} en Factura {self.factura.numero_factura}"

    def save(self, *args, **kwargs):
        self.subtotal_item = self.precio_unitario * self.cantidad
        super().save(*args, **kwargs)
        try:
            agg = self.factura.items_factura.aggregate(s=models.Sum('subtotal_item'))['s'] or Decimal('0.00')
            self.factura.subtotal = agg
            self.factura.save(update_fields=['subtotal', 'monto_total', 'saldo_pendiente', 'estado'])
        except Exception:
            logger.exception(f"Failed to recalculate totals for Factura {self.factura_id} after saving ItemFactura {self.pk}")
"""Modelos de Cotizaciones.

Estos modelos se separan en su propia app `cotizaciones` para romper dependencias
circulares y permitir una carga controlada.
"""
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import User
from decimal import Decimal

from personas.models import Cliente

class Cotizacion(models.Model):
    id_cotizacion = models.AutoField(primary_key=True, verbose_name=_("ID Cotización"))
    numero_cotizacion = models.CharField(_("Número de Cotización"), max_length=50, unique=True, blank=True)
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, verbose_name=_("Cliente"))
    destino = models.CharField(_("Destino del Viaje"), max_length=200, blank=True, null=True)
    consultor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("Consultor"))
    numero_pasajeros = models.PositiveIntegerField(_("Número de Pasajeros"), default=1)
    fecha_emision = models.DateField(_("Fecha de Emisión"), default=timezone.now)
    fecha_vencimiento = models.DateField(_("Fecha de Vencimiento"), blank=True, null=True)
    total_cotizado = models.DecimalField(_("Total Cotizado"), max_digits=12, decimal_places=2, default=0, editable=False)
    
    class EstadoCotizacion(models.TextChoices):
        BORRADOR = 'BOR', _('Borrador')
        ENVIADA = 'ENV', _('Enviada al Cliente')
        VISTA = 'VIS', _('Vista por Cliente')
        ACEPTADA = 'ACE', _('Aceptada')
        RECHAZADA = 'REC', _('Rechazada')
        VENCIDA = 'VEN', _('Vencida')
        CONVERTIDA = 'CON', _('Convertida a Venta')
    estado = models.CharField(_("Estado"), max_length=3, choices=EstadoCotizacion.choices, default=EstadoCotizacion.BORRADOR)
    
    terminos_pago = models.TextField(_("Términos de Pago"), blank=True, null=True)
    terminos_cancelacion = models.TextField(_("Términos de Cancelación"), blank=True, null=True)
    notas = models.TextField(_("Notas Internas"), blank=True, null=True)
    archivo_pdf = models.FileField(_("Archivo PDF"), upload_to='cotizaciones_pdf/', blank=True, null=True)
    
    # Campos de seguimiento
    fecha_envio = models.DateTimeField(_("Fecha de Envío"), blank=True, null=True)
    fecha_vista = models.DateTimeField(_("Fecha Vista por Cliente"), blank=True, null=True)
    fecha_respuesta = models.DateTimeField(_("Fecha de Respuesta"), blank=True, null=True)
    email_enviado = models.BooleanField(_("Email Enviado"), default=False)
    venta_generada = models.OneToOneField('core.Venta', on_delete=models.SET_NULL, blank=True, null=True, verbose_name=_("Venta Generada"))

    class Meta:
        verbose_name = _("Cotización")
        verbose_name_plural = _("Cotizaciones")
        ordering = ['-fecha_emision']

    def __str__(self):
        return self.numero_cotizacion or f"COT-{self.id_cotizacion}"

    def save(self, *args, **kwargs):
        if not self.numero_cotizacion:
            # Formato: COT-2025-0001
            last_id = Cotizacion.objects.all().order_by('id_cotizacion').last()
            new_id = (last_id.id_cotizacion + 1) if last_id else 1
            self.numero_cotizacion = f"COT-{self.fecha_emision.strftime('%Y')}-{new_id:04d}"
        super().save(*args, **kwargs)

    def calcular_total(self):
        total = self.items.aggregate(total=models.Sum('costo'))['total'] or Decimal('0.00')
        self.total_cotizado = total
        self.save(update_fields=['total_cotizado'])
    
    def convertir_a_venta(self):
        """Convierte la cotización en una venta"""
        if self.estado != self.EstadoCotizacion.ACEPTADA:
            raise ValueError("Solo se pueden convertir cotizaciones aceptadas")
        
        if self.venta_generada:
            return self.venta_generada
        
        from core.models import Venta
        from django.utils import timezone
        
        # Crear venta
        venta = Venta.objects.create(
            cliente=self.cliente,
            cotizacion_origen=self,
            fecha_venta=timezone.now(),
            descripcion_general=f"Venta generada desde cotización {self.numero_cotizacion}",
            moneda_id=1,  # Asumir USD por defecto
            subtotal=self.total_cotizado,
            total_venta=self.total_cotizado,
            saldo_pendiente=self.total_cotizado,
            tipo_venta=Venta.TipoVenta.B2C,
            canal_origen=Venta.CanalOrigen.ADMIN
        )
        
        # Actualizar cotización
        self.venta_generada = venta
        self.estado = self.EstadoCotizacion.CONVERTIDA
        self.fecha_respuesta = timezone.now()
        self.save(update_fields=['venta_generada', 'estado', 'fecha_respuesta'])
        
        return venta

class ItemCotizacion(models.Model):
    id_item_cotizacion = models.AutoField(primary_key=True, verbose_name=_("ID Item Cotización"))
    cotizacion = models.ForeignKey(Cotizacion, related_name='items', on_delete=models.CASCADE, verbose_name=_("Cotización"))

    class TipoItem(models.TextChoices):
        VUELO = 'VUE', _('Vuelo')
        ALOJAMIENTO = 'ALO', _('Alojamiento')
        ACTIVIDAD = 'ACT', _('Actividad')
        SEGURO = 'SEG', _('Seguro de Viaje')
        OTRO = 'OTR', _('Otro')

    tipo_item = models.CharField(_("Tipo de Item"), max_length=3, choices=TipoItem.choices, default=TipoItem.OTRO)
    descripcion = models.CharField(_("Descripción Principal"), max_length=255, default='')
    detalles_json = models.JSONField(_("Detalles (JSON)"), blank=True, null=True, help_text=_("Estructura de datos específica para el tipo de item"))
    costo = models.DecimalField(_("Costo Total del Item"), max_digits=12, decimal_places=2, default=0)

    class Meta:
        verbose_name = _("Item de Cotización")
        verbose_name_plural = _("Items de Cotización")
        ordering = ['id_item_cotizacion']

    def __str__(self):
        return f"{self.get_tipo_item_display()} - {self.descripcion}"

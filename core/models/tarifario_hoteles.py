from django.db import models
from django.utils.translation import gettext_lazy as _
from decimal import Decimal


class TarifarioProveedor(models.Model):
    """Tarifario de un proveedor (BT Travel, etc.)"""
    proveedor = models.ForeignKey('core.Proveedor', on_delete=models.CASCADE, related_name='tarifarios')
    nombre = models.CharField(max_length=200, verbose_name=_("Nombre"))
    archivo_pdf = models.FileField(upload_to='tarifarios/%Y/%m/', blank=True, verbose_name=_("Archivo PDF"))
    fecha_vigencia_inicio = models.DateField(verbose_name=_("Vigencia Inicio"))
    fecha_vigencia_fin = models.DateField(verbose_name=_("Vigencia Fin"))
    comision_estandar = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('15.00'), verbose_name=_("Comisión Estándar %"))
    activo = models.BooleanField(default=True, verbose_name=_("Activo"))
    fecha_carga = models.DateTimeField(auto_now_add=True, verbose_name=_("Fecha de Carga"))
    notas = models.TextField(blank=True, verbose_name=_("Notas"))
    
    class Meta:
        verbose_name = _("Tarifario de Proveedor")
        verbose_name_plural = _("Tarifarios de Proveedores")
        ordering = ['-fecha_carga']
    
    def __str__(self):
        return f"{self.proveedor.nombre} - {self.nombre}"


class HotelTarifario(models.Model):
    """Hotel dentro de un tarifario"""
    tarifario = models.ForeignKey(TarifarioProveedor, on_delete=models.CASCADE, related_name='hoteles')
    nombre = models.CharField(max_length=200, verbose_name=_("Nombre del Hotel"))
    destino = models.CharField(max_length=100, verbose_name=_("Destino"))
    ubicacion_descripcion = models.TextField(blank=True, verbose_name=_("Ubicación"))
    
    REGIMEN_CHOICES = [
        ('SO', _('Solo Alojamiento')),
        ('SD', _('Solo Desayuno')),
        ('MP', _('Media Pensión')),
        ('PC', _('Pensión Completa')),
        ('TI', _('Todo Incluido')),
    ]
    regimen = models.CharField(max_length=2, choices=REGIMEN_CHOICES, verbose_name=_("Régimen"))
    comision = models.DecimalField(max_digits=5, decimal_places=2, verbose_name=_("Comisión %"))
    
    # Políticas
    politicas = models.TextField(blank=True, verbose_name=_("Políticas"))
    check_in = models.TimeField(default='15:00', verbose_name=_("Check-in"))
    check_out = models.TimeField(default='12:00', verbose_name=_("Check-out"))
    minimo_noches_temporada_baja = models.IntegerField(default=1, verbose_name=_("Mínimo Noches (Temp. Baja)"))
    minimo_noches_temporada_alta = models.IntegerField(default=2, verbose_name=_("Mínimo Noches (Temp. Alta)"))
    
    activo = models.BooleanField(default=True, verbose_name=_("Activo"))
    
    class Meta:
        verbose_name = _("Hotel en Tarifario")
        verbose_name_plural = _("Hoteles en Tarifario")
        unique_together = ['tarifario', 'nombre']
        ordering = ['destino', 'nombre']
    
    def __str__(self):
        return f"{self.nombre} - {self.destino}"


class TipoHabitacion(models.Model):
    """Tipo de habitación de un hotel"""
    hotel = models.ForeignKey(HotelTarifario, on_delete=models.CASCADE, related_name='tipos_habitacion')
    nombre = models.CharField(max_length=100, verbose_name=_("Tipo de Habitación"))
    capacidad_adultos = models.IntegerField(verbose_name=_("Capacidad Adultos"))
    capacidad_ninos = models.IntegerField(default=0, verbose_name=_("Capacidad Niños"))
    capacidad_total = models.IntegerField(verbose_name=_("Capacidad Total"))
    descripcion = models.TextField(blank=True, verbose_name=_("Descripción"))
    
    class Meta:
        verbose_name = _("Tipo de Habitación")
        verbose_name_plural = _("Tipos de Habitación")
        unique_together = ['hotel', 'nombre']
        ordering = ['hotel', 'nombre']
    
    def __str__(self):
        return f"{self.hotel.nombre} - {self.nombre}"


class TarifaHabitacion(models.Model):
    """Tarifa de una habitación por período"""
    tipo_habitacion = models.ForeignKey(TipoHabitacion, on_delete=models.CASCADE, related_name='tarifas')
    
    # Vigencia
    fecha_inicio = models.DateField(verbose_name=_("Fecha Inicio"))
    fecha_fin = models.DateField(verbose_name=_("Fecha Fin"))
    nombre_temporada = models.CharField(max_length=100, blank=True, verbose_name=_("Temporada"))
    
    # Moneda
    MONEDA_CHOICES = [
        ('USD', '$ Dólares'),
        ('EUR', '€ Euros'),
    ]
    moneda = models.CharField(max_length=3, choices=MONEDA_CHOICES, default='USD', verbose_name=_("Moneda"))
    
    # Tipo de tarifa
    TIPO_TARIFA_CHOICES = [
        ('POR_PERSONA', 'Por Persona por Noche'),
        ('POR_HABITACION', 'Por Habitación por Noche'),
    ]
    tipo_tarifa = models.CharField(max_length=20, choices=TIPO_TARIFA_CHOICES, default='POR_PERSONA', verbose_name=_("Tipo de Tarifa"))
    
    # Tarifas por ocupación
    tarifa_sgl = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name=_("SGL (Simple)"))
    tarifa_dbl = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name=_("DBL (Doble)"))
    tarifa_tpl = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name=_("TPL (Triple)"))
    

    
    class Meta:
        verbose_name = _("Tarifa de Habitación")
        verbose_name_plural = _("Tarifas de Habitaciones")
        ordering = ['tipo_habitacion', 'fecha_inicio']
    
    def __str__(self):
        return f"{self.tipo_habitacion} - {self.fecha_inicio} al {self.fecha_fin}"

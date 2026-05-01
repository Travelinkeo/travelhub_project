from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils.text import slugify
from decimal import Decimal

# --- NUEVO: Servicios/Amenidades ---
class Amenity(models.Model):
    """Servicios como Wifi, Piscina, Estacionamiento, etc."""
    nombre = models.CharField(max_length=100, unique=True, verbose_name=_("Nombre"))
    icono_lucide = models.CharField(max_length=50, default='check', verbose_name=_("Icono Lucide"), help_text="Nombre del icono de Lucide React")
    
    def __str__(self):
        return self.nombre

class TarifarioProveedor(models.Model):
    """Tarifario de un proveedor (BT Travel, etc.)"""
    proveedor = models.ForeignKey('core.Proveedor', on_delete=models.CASCADE, related_name='tarifarios', null=True, blank=True)
    nombre = models.CharField(max_length=200, verbose_name=_("Nombre"))
    archivo_pdf = models.FileField(upload_to='tarifarios/%Y/%m/', blank=True, null=True, verbose_name=_("Archivo PDF"))
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

class ComisionOverrideAerolinea(models.Model):
    """
    Overrides de comisión para aerolíneas específicas dentro de un tarifario.
    Ej: Tarifario BT Travel (General 1%) -> Override Avianca (3%).
    """
    tarifario = models.ForeignKey(TarifarioProveedor, on_delete=models.CASCADE, related_name='overrides_aerolinea')
    aerolinea = models.ForeignKey('core.Aerolinea', on_delete=models.CASCADE, verbose_name=_("Aerolínea"))
    comision_porcentaje = models.DecimalField(max_digits=5, decimal_places=2, verbose_name=_("Comisión Especial %"))
    notas = models.TextField(blank=True, verbose_name=_("Notas Internas"))

    class Meta:
        verbose_name = _("Comisión Especial por Aerolínea")
        verbose_name_plural = _("Comisiones Especiales (Overrides)")
        unique_together = ('tarifario', 'aerolinea')

    def __str__(self):
        return f"{self.aerolinea.nombre}: {self.comision_porcentaje}%"


class HotelTarifario(models.Model):
    """Hotel extraido de un tarifario (o cargado manualmente)"""
    tarifario = models.ForeignKey(TarifarioProveedor, on_delete=models.CASCADE, related_name='hoteles', null=True, blank=True)
    nombre = models.CharField(max_length=200, verbose_name=_("Nombre del Hotel"))
    slug = models.SlugField(max_length=250, unique=True, null=True, blank=True, help_text="URL amigable")
    
    # Geolocalización & Destino
    destino = models.CharField(max_length=100, verbose_name=_("Destino")) # Ej: Morrocoy, Margarita
    direccion = models.TextField(blank=True, verbose_name=_("Dirección Completa"))
    coordenadas_mapa = models.CharField(max_length=100, blank=True, help_text="Lat,Long para Google Maps")
    
    # Contenido Rico (IA Vision)
    descripcion_corta = models.TextField(blank=True, verbose_name=_("Descripción Corta"), help_text="Para listados")
    descripcion_larga = models.TextField(blank=True, verbose_name=_("Descripción Completa (IA)"))
    
    # Media
    imagen_principal = models.ImageField(upload_to='hoteles/portadas/', blank=True, null=True, verbose_name=_("Imagen Portada"))
    logo = models.ImageField(upload_to='hoteles/logos/', blank=True, null=True, verbose_name=_("Logo del Hotel"))
    video_promocional = models.FileField(upload_to='hoteles/videos/', blank=True, null=True, verbose_name=_("Video Promocional"), help_text="Video corto para la ficha del hotel")
    
    # Clasificación
    CATEGORIA_CHOICES = [
        (1, 'Eco / Posada'),
        (2, 'Estandar'),
        (3, 'Confort'),
        (4, 'Lujo'),
        (5, 'Gran Lujo / Premium'),
    ]
    categoria = models.IntegerField(choices=CATEGORIA_CHOICES, default=3, verbose_name=_("Categoría"))
    
    # Relaciones
    amenidades = models.ManyToManyField(Amenity, blank=True, related_name='hoteles')
    
    # Metadata Operativa
    REGIMEN_CHOICES = [
        ('SO', _('Solo Alojamiento')),
        ('SD', _('Solo Desayuno')),
        ('MP', _('Media Pensión')),
        ('PC', _('Pensión Completa')),
        ('TI', _('Todo Incluido')),
    ]
    regimen_default = models.CharField(max_length=2, choices=REGIMEN_CHOICES, default='SD', verbose_name=_("Régimen Principal"))
    comision = models.DecimalField(max_digits=5, decimal_places=2, verbose_name=_("Comisión %"), default=Decimal('10.00'))
    
    # Políticas
    politicas = models.TextField(blank=True, verbose_name=_("Políticas"))
    check_in = models.TimeField(default='15:00', verbose_name=_("Check-in"))
    check_out = models.TimeField(default='12:00', verbose_name=_("Check-out"))
    
    # SEO & Estado
    activo = models.BooleanField(default=True, verbose_name=_("Activo"))
    destacado = models.BooleanField(default=False, verbose_name=_("Destacado (Home)"))
    
    class Meta:
        verbose_name = _("Hotel")
        verbose_name_plural = _("Hoteles")
        ordering = ['destino', 'nombre']
    
    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(f"{self.nombre}-{self.destino}")
            slug = base_slug
            counter = 1
            # Check for duplicates (excluding self if editing)
            while HotelTarifario.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.nombre} ({self.destino})"

class ImagenHotel(models.Model):
    """Galería de fotos del hotel"""
    hotel = models.ForeignKey(HotelTarifario, on_delete=models.CASCADE, related_name='imagenes', null=True, blank=True)
    imagen = models.ImageField(upload_to='hoteles/galeria/')
    titulo = models.CharField(max_length=100, blank=True)
    
    TIPO_CHOICES = [
        ('GENERAL', 'General'),
        ('HABITACION', 'Habitación'),
        ('COMIDA', 'Restaurante/Comida'),
        ('PLAYA', 'Playa/Piscina'),
    ]
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='GENERAL')
    es_portada = models.BooleanField(default=False)
    
    def __str__(self):
        return f"Foto {self.hotel.nombre} - {self.tipo}"


class TipoHabitacion(models.Model):
    """Tipo de habitación de un hotel"""
    hotel = models.ForeignKey(HotelTarifario, on_delete=models.CASCADE, related_name='tipos_habitacion', null=True, blank=True)
    nombre = models.CharField(max_length=100, verbose_name=_("Tipo de Habitación")) # Ej: Matrimonial Standard
    
    # Capacidad
    capacidad_adultos = models.IntegerField(default=2, verbose_name=_("Max Adultos"))
    capacidad_ninos = models.IntegerField(default=1, verbose_name=_("Max Niños"))
    capacidad_total = models.IntegerField(default=3, verbose_name=_("Max Total"))
    
    descripcion = models.TextField(blank=True, verbose_name=_("Descripción"))
    foto_referencial = models.ImageField(upload_to='hoteles/habitaciones/', blank=True, null=True)
    
    class Meta:
        verbose_name = _("Tipo de Habitación")
        verbose_name_plural = _("Tipos de Habitación")
        unique_together = ['hotel', 'nombre']
        ordering = ['hotel', 'nombre']
    
    def __str__(self):
        return f"{self.hotel.nombre} - {self.nombre}"


class TarifaHabitacion(models.Model):
    """Tarifa de una habitación por período"""
    tipo_habitacion = models.ForeignKey(TipoHabitacion, on_delete=models.CASCADE, related_name='tarifas', null=True, blank=True)
    
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
    
    # Tarifas por ocupación (Precios Netos o PVP?) Asumiremos PVP por ahora
    tarifa_sgl = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name=_("SGL (Simple)"))
    tarifa_dbl = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name=_("DBL (Doble)"))
    tarifa_tpl = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name=_("TPL (Triple)"))
    tarifa_cpl = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name=_("CPL (Cuadruple)"))
    
    tarifa_nino = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name=_("Tarifa Niño"))
    
    class Meta:
        verbose_name = _("Tarifa de Habitación")
        verbose_name_plural = _("Tarifas de Habitaciones")
        ordering = ['tipo_habitacion', 'fecha_inicio']
    
    def __str__(self):
        return f"{self.tipo_habitacion} - {self.fecha_inicio:%d/%m} al {self.fecha_fin:%d/%m}"

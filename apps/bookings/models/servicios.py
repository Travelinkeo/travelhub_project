# apps/bookings/models/servicios.py
"""
Modelos de Productos y Servicios (Migrado desde core)
Incluye: Proveedor, ProductoServicio, ComisionProveedorServicio, ProductoTerrestre.
"""
from django.db import models
from django.utils.translation import gettext_lazy as _
from decimal import Decimal
from core.managers import TenantManager
from core.models.base import AgenciaMixin
from core.mixins import SoftDeleteModel
from core.validators import validar_no_vacio_o_espacios

class Proveedor(SoftDeleteModel, AgenciaMixin, models.Model):
    id_proveedor = models.AutoField(primary_key=True, verbose_name=_("ID Proveedor"))
    nombre = models.CharField(_("Nombre del Proveedor"), max_length=150, unique=True, validators=[validar_no_vacio_o_espacios])
    alias = models.CharField(_("Alias/Nombre Comercial"), max_length=150, blank=True, null=True, help_text=_("Nombre con el que es conocido en el mercado"))
    rif = models.CharField(_("RIF"), max_length=20, blank=True, null=True, help_text=_("Registro de Información Fiscal"))

    class TipoProveedorChoices(models.TextChoices):
        AEROLINEA = 'AER', _('Aerolínea')
        HOTEL = 'HTL', _('Hotel')
        OPERADOR_TURISTICO = 'OPT', _('Operador Turístico')
        CONSOLIDADOR = 'CON', _('Consolidador')
        MAYORISTA = 'MAY', _('Mayorista')
        SEGUROS = 'SEG', _('Seguros')
        TRANSPORTE = 'TRN', _('Transporte Terrestre')
        GDS = 'GDS', _('Sistema de Distribución Global (GDS)')
        OTRO = 'OTR', _('Otro')
    tipo_proveedor = models.CharField(_("Tipo de Proveedor"), max_length=3, choices=TipoProveedorChoices.choices, default=TipoProveedorChoices.OTRO)

    class NivelProveedorChoices(models.TextChoices):
        DIRECTO = 'DIR', _('Directo')
        CONSOLIDADOR = 'CON', _('Consolidador')
        MAYORISTA = 'MAY', _('Mayorista')
        TERCERO = 'TER', _('Otro (Tercero)')
    nivel_proveedor = models.CharField(_("Nivel del Proveedor"), max_length=3, choices=NivelProveedorChoices.choices, default=NivelProveedorChoices.DIRECTO, help_text=_("Nivel de intermediación del proveedor."))

    contacto_nombre = models.CharField(_("Nombre de Contacto"), max_length=100, blank=True, null=True)
    contacto_email = models.EmailField(_("Email de Contacto"), max_length=255, blank=True, null=True)
    contacto_telefono = models.CharField(_("Teléfono de Contacto"), max_length=30, blank=True, null=True)
    direccion = models.CharField(_("Dirección"), max_length=255, blank=True, null=True)
    ciudad = models.ForeignKey('common.Ciudad', on_delete=models.SET_NULL, blank=True, null=True, verbose_name=_("Ciudad"))
    notas = models.TextField(_("Notas sobre el Proveedor"), blank=True, null=True)
    numero_cuenta_agencia = models.CharField(_("Número de Cuenta/IATA con el Proveedor"), max_length=50, blank=True, null=True)
    condiciones_pago = models.CharField(_("Condiciones de Pago"), max_length=100, blank=True, null=True)
    datos_bancarios = models.TextField(_("Datos Bancarios del Proveedor"), blank=True, null=True)
    
    fee_nacional = models.DecimalField(_("Fee Nacional"), max_digits=10, decimal_places=2, blank=True, null=True, help_text=_("Fee por servicios nacionales"))
    fee_internacional = models.DecimalField(_("Fee Internacional"), max_digits=10, decimal_places=2, blank=True, null=True, help_text=_("Fee por servicios internacionales"))
    
    activo = models.BooleanField(_("Activo"), default=True)
    
    identificadores_gds = models.JSONField(
        _("Identificadores GDS (IATA/OfficeID)"), 
        blank=True, null=True, default=dict
    )

    iata = models.CharField(_("IATA"), max_length=10, blank=True, null=True)
    seudo_sabre = models.CharField(_("Seudo SABRE"), max_length=4, blank=True, null=True)
    office_id_kiu = models.CharField(_("Office ID KIU"), max_length=8, blank=True, null=True)
    office_id_amadeus = models.CharField(_("Office ID AMADEUS"), max_length=10, blank=True, null=True)
    office_id_travelport = models.CharField(_("Office ID TRAVELPORT"), max_length=10, blank=True, null=True)
    office_id_hotelbeds = models.CharField(_("Office ID HOTEL BEDS"), max_length=10, blank=True, null=True)
    office_id_expedia = models.CharField(_("Office ID EXPEDIA"), max_length=10, blank=True, null=True)

    class Meta:
        verbose_name = _("Proveedor")
        verbose_name_plural = _("Proveedores")
        ordering = ['nombre']
        db_table = 'core_proveedor'

    def __str__(self):
        return f"{self.nombre} ({self.get_tipo_proveedor_display()})"

class ProductoServicio(SoftDeleteModel, AgenciaMixin, models.Model):
    id_producto_servicio = models.AutoField(primary_key=True, verbose_name=_("ID Producto/Servicio"))
    codigo_interno = models.CharField(_("Código Interno"), max_length=50, unique=True, blank=True, null=True)
    nombre = models.CharField(_("Nombre del Producto/Servicio"), max_length=255, validators=[validar_no_vacio_o_espacios])
    descripcion = models.TextField(_("Descripción"), blank=True, null=True)
    
    class TipoProductoChoices(models.TextChoices):
        BOLETO_AEREO = 'AIR', _('Boleto Aéreo')
        HOTEL = 'HTL', _('Alojamiento (Hotel)')
        PAQUETE_TURISTICO = 'PKG', _('Paquete Turístico')
        TOUR_ACTIVIDAD = 'TOU', _('Tour o Actividad')
        TRASLADO = 'TRF', _('Traslado')
        SEGURO_VIAJE = 'INS', _('Seguro de Viaje')
        CRUCERO = 'CRU', _('Crucero')
        ALQUILER_AUTO = 'CAR', _('Alquiler de Auto')
        SERVICIO_ADICIONAL = 'SVC', _('Servicio Adicional')
        OTRO = 'OTR', _('Otro')
    
    tipo_producto = models.CharField(_("Tipo de Producto/Servicio"), max_length=3, choices=TipoProductoChoices.choices, default=TipoProductoChoices.OTRO)
    proveedor_principal = models.ForeignKey(Proveedor, on_delete=models.SET_NULL, blank=True, null=True)
    costo_estandar_referencial = models.DecimalField(_("Costo Estándar Referencial"), max_digits=12, decimal_places=2, blank=True, null=True)
    precio_venta_sugerido = models.DecimalField(_("Precio de Venta Sugerido"), max_digits=12, decimal_places=2, blank=True, null=True)
    moneda_referencial = models.ForeignKey('finance.Moneda', on_delete=models.SET_NULL, blank=True, null=True)
    activo = models.BooleanField(_("Activo"), default=True)

    class Meta:
        verbose_name = _("Producto o Servicio")
        verbose_name_plural = _("Productos y Servicios")
        ordering = ['nombre']
        unique_together = ('agencia', 'nombre', 'tipo_producto', 'proveedor_principal')
        db_table = 'core_productoservicio'

    def __str__(self):
        return f"{self.nombre} ({self.get_tipo_producto_display()})"

class ComisionProveedorServicio(SoftDeleteModel, AgenciaMixin, models.Model):
    id_comision = models.AutoField(primary_key=True, verbose_name=_("ID Comisión"))
    proveedor = models.ForeignKey(Proveedor, on_delete=models.CASCADE, related_name='comisiones', null=True, blank=True)
    tipo_servicio = models.CharField(_("Tipo de Servicio"), max_length=3, choices=ProductoServicio.TipoProductoChoices.choices)
    comision_porcentaje = models.DecimalField(_("Comisión (%)"), max_digits=5, decimal_places=2, blank=True, null=True)
    comision_monto_fijo = models.DecimalField(_("Comisión Monto Fijo"), max_digits=10, decimal_places=2, blank=True, null=True)
    moneda = models.ForeignKey('finance.Moneda', on_delete=models.PROTECT, blank=True, null=True)
    activo = models.BooleanField(_("Activo"), default=True)
    
    class Meta:
        verbose_name = _("Comisión de Proveedor por Servicio")
        verbose_name_plural = _("Comisiones de Proveedores por Servicios")
        unique_together = ('agencia', 'proveedor', 'tipo_servicio')
        db_table = 'core_comisionproveedorservicio'
    
    def __str__(self):
        return f"{self.proveedor.nombre} - {self.get_tipo_servicio_display()}"

class ProductoTerrestre(SoftDeleteModel, AgenciaMixin, models.Model):
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
    descripcion_publica = models.TextField(_("Descripción (Pública)"), blank=True, null=True)
    
    costo_neto = models.DecimalField(_("Costo Neto (Proveedor)"), max_digits=12, decimal_places=2)
    markup_porcentaje = models.DecimalField(_("Markup (Ganancia %)"), max_digits=5, decimal_places=2, default=Decimal('20.00'))
    precio_venta_calculado = models.DecimalField(_("Precio Venta"), max_digits=12, decimal_places=2, editable=False)
    
    imagen_principal = models.ImageField(_("Foto Principal"), upload_to='productos_terrestres/%Y/%m/', blank=True, null=True)
    activo = models.BooleanField(_("Activo"), default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)


    class Meta:
        verbose_name = _("Producto Terrestre")
        verbose_name_plural = _("Productos Terrestres")
        ordering = ['-fecha_creacion']
        db_table = 'core_productoterrestre'

    def save(self, *args, **kwargs):
        self.precio_venta_calculado = self.costo_neto + (self.costo_neto * (self.markup_porcentaje / Decimal('100.00')))
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.nombre} ({self.get_tipo_servicio_display()})"


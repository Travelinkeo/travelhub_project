"""Modelos de catálogos (extraídos de core.models en Fase 1).

Incluye: Pais, Ciudad, Moneda, TipoCambio, Proveedor, ProductoServicio.
Las definiciones son idénticas a la versión previa para evitar migraciones.
"""
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .validators import validar_no_vacio_o_espacios


class Pais(models.Model):
    id_pais = models.AutoField(primary_key=True, verbose_name=_("ID País"))
    codigo_iso_2 = models.CharField(_("Código ISO 2"), max_length=2, unique=True, help_text=_("Código ISO 3166-1 alfa-2 del país."))
    codigo_iso_3 = models.CharField(_("Código ISO 3"), max_length=3, unique=True, help_text=_("Código ISO 3166-1 alfa-3 del país."))
    nombre = models.CharField(_("Nombre del País"), max_length=100, unique=True, validators=[validar_no_vacio_o_espacios])
    class Meta:
        verbose_name = _("País")
        verbose_name_plural = _("Países")
        ordering = ['nombre']
    def __str__(self):  # pragma: no cover
        return self.nombre

class Ciudad(models.Model):
    id_ciudad = models.AutoField(primary_key=True, verbose_name=_("ID Ciudad"))
    nombre = models.CharField(_("Nombre de la Ciudad"), max_length=100, validators=[validar_no_vacio_o_espacios])
    pais = models.ForeignKey(Pais, on_delete=models.PROTECT, verbose_name=_("País"))
    region_estado = models.CharField(_("Región/Estado"), max_length=100, blank=True, null=True)
    class Meta:
        verbose_name = _("Ciudad")
        verbose_name_plural = _("Ciudades")
        ordering = ['pais__nombre', 'nombre']
        unique_together = ('nombre', 'pais', 'region_estado')
    def __str__(self):  # pragma: no cover
        return f"{self.nombre}{f', {self.region_estado}' if self.region_estado else ''} ({self.pais.nombre})"

class Moneda(models.Model):
    id_moneda = models.AutoField(primary_key=True, verbose_name=_("ID Moneda"))
    codigo_iso = models.CharField(_("Código ISO"), max_length=3, unique=True, help_text=_("Código ISO 4217 de la moneda (ej. USD, EUR, VEF)."))
    nombre = models.CharField(_("Nombre de la Moneda"), max_length=50, unique=True, validators=[validar_no_vacio_o_espacios])
    simbolo = models.CharField(_("Símbolo"), max_length=5, blank=True, null=True)
    es_moneda_local = models.BooleanField(_("Es Moneda Local"), default=False, help_text=_("Marcar si esta es la moneda principal de la agencia."))
    class Meta:
        verbose_name = _("Moneda")
        verbose_name_plural = _("Monedas")
        ordering = ['nombre']
    def __str__(self):  # pragma: no cover
        return f"{self.nombre} ({self.codigo_iso})"

class TipoCambio(models.Model):
    id_tipo_cambio = models.AutoField(primary_key=True, verbose_name=_("ID Tipo de Cambio"))
    moneda_origen = models.ForeignKey(Moneda, related_name='tipos_cambio_origen', on_delete=models.PROTECT, verbose_name=_("Moneda Origen"))
    moneda_destino = models.ForeignKey(Moneda, related_name='tipos_cambio_destino', on_delete=models.PROTECT, verbose_name=_("Moneda Destino"))
    fecha_efectiva = models.DateField(_("Fecha Efectiva"), default=timezone.now, help_text=_("Fecha en que esta tasa de cambio entra en vigor."))
    tasa_conversion = models.DecimalField(_("Tasa de Conversión"), max_digits=18, decimal_places=8, help_text=_("Cuánto de la moneda destino equivale a 1 unidad de la moneda origen."))
    class Meta:
        verbose_name = _("Tipo de Cambio")
        verbose_name_plural = _("Tipos de Cambio")
        ordering = ['-fecha_efectiva', 'moneda_origen__codigo_iso']
        unique_together = ('moneda_origen', 'moneda_destino', 'fecha_efectiva')
    def __str__(self):  # pragma: no cover
        return f"{self.moneda_origen.codigo_iso} a {self.moneda_destino.codigo_iso} el {self.fecha_efectiva}: {self.tasa_conversion}"
    def clean(self):  # pragma: no cover - lógica simple
        if self.moneda_origen == self.moneda_destino:
            raise ValidationError(_("La moneda de origen y destino no pueden ser la misma."))
        if self.tasa_conversion <= 0:
            raise ValidationError(_("La tasa de conversión debe ser un valor positivo."))

class Proveedor(models.Model):
    id_proveedor = models.AutoField(primary_key=True, verbose_name=_("ID Proveedor"))
    nombre = models.CharField(_("Nombre del Proveedor"), max_length=150, unique=True, validators=[validar_no_vacio_o_espacios])

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
    ciudad = models.ForeignKey(Ciudad, on_delete=models.SET_NULL, blank=True, null=True, verbose_name=_("Ciudad"))
    notas = models.TextField(_("Notas sobre el Proveedor"), blank=True, null=True)
    numero_cuenta_agencia = models.CharField(_("Número de Cuenta/IATA con el Proveedor"), max_length=50, blank=True, null=True)
    condiciones_pago = models.CharField(_("Condiciones de Pago"), max_length=100, blank=True, null=True)
    datos_bancarios = models.TextField(_("Datos Bancarios del Proveedor"), blank=True, null=True)
    activo = models.BooleanField(_("Activo"), default=True, help_text=_("Indica si el proveedor está actualmente activo."))

    # --- Campos de Identificación GDS y Sistemas --- 
    iata = models.CharField(_("IATA"), max_length=10, blank=True, null=True, help_text=_("Número IATA del proveedor"))
    seudo_sabre = models.CharField(_("Seudo SABRE"), max_length=4, blank=True, null=True)
    office_id_kiu = models.CharField(_("Office ID KIU"), max_length=8, blank=True, null=True)
    office_id_amadeus = models.CharField(_("Office ID AMADEUS"), max_length=10, blank=True, null=True)
    office_id_travelport = models.CharField(_("Office ID TRAVELPORT"), max_length=10, blank=True, null=True)
    office_id_hotelbeds = models.CharField(_("Office ID HOTEL BEDS"), max_length=10, blank=True, null=True)
    office_id_expedia = models.CharField(_("Office ID EXPEDIA"), max_length=10, blank=True, null=True)

    # --- Otros Sistemas de Reserva --- 
    otro_sistema_1_nombre = models.CharField(_("Otro Sistema 1: Nombre"), max_length=50, blank=True, null=True)
    otro_sistema_1_id = models.CharField(_("Otro Sistema 1: ID"), max_length=50, blank=True, null=True)
    
    otro_sistema_2_nombre = models.CharField(_("Otro Sistema 2: Nombre"), max_length=50, blank=True, null=True)
    otro_sistema_2_id = models.CharField(_("Otro Sistema 2: ID"), max_length=50, blank=True, null=True)

    otro_sistema_3_nombre = models.CharField(_("Otro Sistema 3: Nombre"), max_length=50, blank=True, null=True)
    otro_sistema_3_id = models.CharField(_("Otro Sistema 3: ID"), max_length=50, blank=True, null=True)

    otro_sistema_4_nombre = models.CharField(_("Otro Sistema 4: Nombre"), max_length=50, blank=True, null=True)
    otro_sistema_4_id = models.CharField(_("Otro Sistema 4: ID"), max_length=50, blank=True, null=True)

    otro_sistema_5_nombre = models.CharField(_("Otro Sistema 5: Nombre"), max_length=50, blank=True, null=True)
    otro_sistema_5_id = models.CharField(_("Otro Sistema 5: ID"), max_length=50, blank=True, null=True)

    class Meta:
        verbose_name = _("Proveedor")
        verbose_name_plural = _("Proveedores")
        ordering = ['nombre']

    def __str__(self):  # pragma: no cover
        return f"{self.nombre} ({self.get_tipo_proveedor_display()})"

class ProductoServicio(models.Model):
    id_producto_servicio = models.AutoField(primary_key=True, verbose_name=_("ID Producto/Servicio"))
    codigo_interno = models.CharField(_("Código Interno"), max_length=50, unique=True, blank=True, null=True, help_text=_("Código interno de la agencia para este producto/servicio."))
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
    proveedor_principal = models.ForeignKey(Proveedor, on_delete=models.SET_NULL, blank=True, null=True, verbose_name=_("Proveedor Principal/Preferido"))
    costo_estandar_referencial = models.DecimalField(_("Costo Estándar Referencial"), max_digits=12, decimal_places=2, blank=True, null=True, help_text=_("Costo aproximado para la agencia."))
    precio_venta_sugerido = models.DecimalField(_("Precio de Venta Sugerido"), max_digits=12, decimal_places=2, blank=True, null=True)
    moneda_referencial = models.ForeignKey(Moneda, on_delete=models.SET_NULL, blank=True, null=True, verbose_name=_("Moneda Referencial"))
    activo = models.BooleanField(_("Activo"), default=True, help_text=_("Indica si este producto/servicio está actualmente ofrecido."))
    requiere_datos_pasajero_especificos = models.BooleanField(_("Requiere Datos Específicos del Pasajero"), default=False, help_text=_("Ej. para boletos aéreos, seguros."))
    class Meta:
        verbose_name = _("Producto o Servicio")
        verbose_name_plural = _("Productos y Servicios")
        ordering = ['nombre']
        unique_together = ('nombre', 'tipo_producto', 'proveedor_principal')
    def __str__(self):  # pragma: no cover
        return f"{self.nombre} ({self.get_tipo_producto_display()})"

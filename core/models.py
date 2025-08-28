# Archivo: core/models.py
import json
import re
from decimal import Decimal, InvalidOperation
import datetime
import traceback
import logging

import fitz
from eml_parser import EmlParser
from bs4 import BeautifulSoup

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.urls import reverse, NoReverseMatch
from django.core.files.base import ContentFile

from . import ticket_parser
from . import pdf_generator

logger = logging.getLogger(__name__)

def validar_no_vacio_o_espacios(value):
    if isinstance(value, str) and not value.strip():
        raise ValidationError(_('Este campo no puede consistir únicamente en espacios en blanco.'))

def validar_numero_pasaporte(value):
    if value and not re.match(r'^[A-Z0-9]+$', value.upper()):
        raise ValidationError(_('El número de pasaporte solo puede contener letras y números.'))

# --- Modelos de Configuración / Compartidos ---
class Pais(models.Model):
    id_pais = models.AutoField(primary_key=True, verbose_name=_("ID País"))
    codigo_iso_2 = models.CharField(_("Código ISO 2"), max_length=2, unique=True, help_text=_("Código ISO 3166-1 alfa-2 del país."))
    codigo_iso_3 = models.CharField(_("Código ISO 3"), max_length=3, unique=True, help_text=_("Código ISO 3166-1 alfa-3 del país."))
    nombre = models.CharField(_("Nombre del País"), max_length=100, unique=True, validators=[validar_no_vacio_o_espacios])

    class Meta:
        verbose_name = _("País")
        verbose_name_plural = _("Países")
        ordering = ['nombre']

    def __str__(self):
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

    def __str__(self):
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

    def __str__(self):
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

    def __str__(self):
        return f"{self.moneda_origen.codigo_iso} a {self.moneda_destino.codigo_iso} el {self.fecha_efectiva}: {self.tasa_conversion}"

    def clean(self):
        if self.moneda_origen == self.moneda_destino:
            raise ValidationError(_("La moneda de origen y destino no pueden ser la misma."))
        if self.tasa_conversion <= 0:
            raise ValidationError(_("La tasa de conversión debe ser un valor positivo."))

class Cliente(models.Model):
    id_cliente = models.AutoField(primary_key=True, verbose_name=_("ID Cliente"))
    nombres = models.CharField(_("Nombres"), max_length=100, validators=[validar_no_vacio_o_espacios])
    apellidos = models.CharField(_("Apellidos"), max_length=100, blank=True, null=True)
    nombre_empresa = models.CharField(_("Nombre de Empresa"), max_length=150, blank=True, null=True)
    email = models.EmailField(_("Correo Electrónico"), max_length=255, unique=True, blank=True, null=True)
    telefono_principal = models.CharField(_("Teléfono Principal"), max_length=30, blank=True, null=True)
    telefono_secundario = models.CharField(_("Teléfono Secundario"), max_length=30, blank=True, null=True)
    direccion_linea1 = models.CharField(_("Dirección Línea 1"), max_length=255, blank=True, null=True)
    direccion_linea2 = models.CharField(_("Dirección Línea 2"), max_length=255, blank=True, null=True)
    ciudad = models.ForeignKey(Ciudad, on_delete=models.SET_NULL, blank=True, null=True, verbose_name=_("Ciudad"))
    codigo_postal = models.CharField(_("Código Postal"), max_length=20, blank=True, null=True)
    fecha_nacimiento = models.DateField(_("Fecha de Nacimiento"), blank=True, null=True)
    numero_pasaporte = models.CharField(_("Número de Pasaporte"), max_length=50, blank=True, null=True, validators=[validar_numero_pasaporte])
    pais_emision_pasaporte = models.ForeignKey(Pais, related_name='clientes_pasaporte_emitido', on_delete=models.SET_NULL, blank=True, null=True, verbose_name=_("País Emisión Pasaporte"))
    fecha_vencimiento_pasaporte = models.DateField(_("Fecha Vencimiento Pasaporte"), blank=True, null=True)
    nacionalidad = models.ForeignKey(Pais, related_name='clientes_nacionalidad', on_delete=models.SET_NULL, blank=True, null=True, verbose_name=_("Nacionalidad"))
    preferencias_viaje = models.TextField(_("Preferencias de Viaje"), blank=True, null=True)
    notas_cliente = models.TextField(_("Notas sobre el Cliente"), blank=True, null=True)
    fecha_registro = models.DateTimeField(_("Fecha de Registro"), default=timezone.now)
    class TipoCliente(models.TextChoices): INDIVIDUAL = 'IND', _('Individual'); CORPORATIVO = 'COR', _('Corporativo'); VIP = 'VIP', _('VIP'); OTRO = 'OTR', _('Otro')
    tipo_cliente = models.CharField(_("Tipo de Cliente"), max_length=3, choices=TipoCliente.choices, default=TipoCliente.INDIVIDUAL)
    puntos_fidelidad = models.PositiveIntegerField(_("Puntos de Fidelidad"), default=0, help_text=_("Puntos acumulados por el cliente."))
    es_cliente_frecuente = models.BooleanField(_("Es Cliente Frecuente"), default=False, editable=False)
    class Meta:
        verbose_name = _("Cliente")
        verbose_name_plural = _("Clientes")
        ordering = ['apellidos', 'nombres', 'nombre_empresa']
    def __str__(self): return self.nombre_empresa if self.nombre_empresa else f"{self.nombres} {self.apellidos or ''}".strip()
    def get_nombre_completo(self): return f"{self.nombres} {self.apellidos or ''}".strip()
    get_nombre_completo.short_description = _("Nombre Completo")
    def calcular_cliente_frecuente(self, umbral_puntos=1000, umbral_compras=5): self.es_cliente_frecuente = self.puntos_fidelidad >= umbral_puntos; return self.es_cliente_frecuente
    def clean(self):
        if not self.nombre_empresa and (not self.nombres or not self.apellidos): raise ValidationError(_("Si no es una empresa, debe proporcionar nombres y apellidos."))
        if self.email and Cliente.objects.filter(email=self.email).exclude(pk=self.pk).exists(): raise ValidationError({'email': _('Ya existe un cliente con este correo electrónico.')})

class Pasajero(models.Model):
    id_pasajero = models.AutoField(primary_key=True, verbose_name=_("ID Pasajero"))
    nombres = models.CharField(_("Nombres"), max_length=100, validators=[validar_no_vacio_o_espacios])
    apellidos = models.CharField(_("Apellidos"), max_length=100, validators=[validar_no_vacio_o_espacios])
    fecha_nacimiento = models.DateField(_("Fecha de Nacimiento"), blank=True, null=True)
    
    class TipoDocumentoChoices(models.TextChoices):
        PASAPORTE = 'PASS', _('Pasaporte')
        CEDULA = 'CI', _('Cédula de Identidad')
        OTRO = 'OTRO', _('Otro')

    tipo_documento = models.CharField(_("Tipo de Documento"), max_length=4, choices=TipoDocumentoChoices.choices, default=TipoDocumentoChoices.PASAPORTE)
    numero_documento = models.CharField(_("Número de Documento/Pasaporte"), max_length=50, unique=True, validators=[validar_numero_pasaporte])
    pais_emision_documento = models.ForeignKey(Pais, on_delete=models.SET_NULL, blank=True, null=True, verbose_name=_("País Emisión Documento"))
    fecha_vencimiento_documento = models.DateField(_("Fecha Vencimiento Documento"), blank=True, null=True)
    nacionalidad = models.ForeignKey(Pais, related_name='pasajeros_nacionalidad', on_delete=models.SET_NULL, blank=True, null=True, verbose_name=_("Nacionalidad"))
    email = models.EmailField(_("Correo Electrónico"), max_length=255, blank=True, null=True)
    telefono = models.CharField(_("Teléfono"), max_length=30, blank=True, null=True)
    notas = models.TextField(_("Notas sobre el Pasajero"), blank=True, null=True)

    class Meta:
        verbose_name = _("Pasajero")
        verbose_name_plural = _("Pasajeros")
        ordering = ['apellidos', 'nombres']
        unique_together = ('nombres', 'apellidos', 'fecha_nacimiento')

    def __str__(self):
        return f"{self.nombres} {self.apellidos}"

    def get_nombre_completo(self):
        return f"{self.nombres} {self.apellidos}".strip()

class Proveedor(models.Model):
    id_proveedor = models.AutoField(primary_key=True, verbose_name=_("ID Proveedor"))
    nombre = models.CharField(_("Nombre del Proveedor"), max_length=150, unique=True, validators=[validar_no_vacio_o_espacios])
    class TipoProveedorChoices(models.TextChoices): AEROLINEA = 'AER', _('Aerolínea'); HOTEL = 'HTL', _('Hotel'); OPERADOR_TURISTICO = 'OPT', _('Operador Turístico'); CONSOLIDADOR = 'CON', _('Consolidador'); MAYORISTA = 'MAY', _('Mayorista'); SEGUROS = 'SEG', _('Seguros'); TRANSPORTE = 'TRN', _('Transporte Terrestre'); GDS = 'GDS', _('Sistema de Distribución Global (GDS)'); OTRO = 'OTR', _('Otro')
    tipo_proveedor = models.CharField(_("Tipo de Proveedor"), max_length=3, choices=TipoProveedorChoices.choices, default=TipoProveedorChoices.OTRO)
    class NivelProveedorChoices(models.TextChoices): DIRECTO = 'DIR', _('Directo'); CONSOLIDADOR = 'CON', _('Consolidador'); MAYORISTA = 'MAY', _('Mayorista'); TERCERO = 'TER', _('Otro (Tercero)')
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
    class Meta:
        verbose_name = _("Proveedor")
        verbose_name_plural = _("Proveedores")
        ordering = ['nombre']
    def __str__(self): return f"{self.nombre} ({self.get_tipo_proveedor_display()})"

class ProductoServicio(models.Model):
    id_producto_servicio = models.AutoField(primary_key=True, verbose_name=_("ID Producto/Servicio"))
    codigo_interno = models.CharField(_("Código Interno"), max_length=50, unique=True, blank=True, null=True, help_text=_("Código interno de la agencia para este producto/servicio."))
    nombre = models.CharField(_("Nombre del Producto/Servicio"), max_length=255, validators=[validar_no_vacio_o_espacios])
    descripcion = models.TextField(_("Descripción"), blank=True, null=True)
    class TipoProductoChoices(models.TextChoices): BOLETO_AEREO = 'AIR', _('Boleto Aéreo'); HOTEL = 'HTL', _('Alojamiento (Hotel)'); PAQUETE_TURISTICO = 'PKG', _('Paquete Turístico'); TOUR_ACTIVIDAD = 'TOU', _('Tour o Actividad'); TRASLADO = 'TRF', _('Traslado'); SEGURO_VIAJE = 'INS', _('Seguro de Viaje'); CRUCERO = 'CRU', _('Crucero'); ALQUILER_AUTO = 'CAR', _('Alquiler de Auto'); SERVICIO_ADICIONAL = 'SVC', _('Servicio Adicional'); OTRO = 'OTR', _('Otro')
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
    def __str__(self): return f"{self.nombre} ({self.get_tipo_producto_display()})"

class Cotizacion(models.Model):
    id_cotizacion = models.AutoField(primary_key=True, verbose_name=_("ID Cotización"))
    numero_cotizacion = models.CharField(_("Número de Cotización"), max_length=20, unique=True, blank=True, help_text=_("Generado automáticamente o manual."))
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, verbose_name=_("Cliente"))
    fecha_emision = models.DateTimeField(_("Fecha de Emisión"), default=timezone.now)
    fecha_validez = models.DateField(_("Válida Hasta"), blank=True, null=True)
    descripcion_general = models.TextField(_("Descripción General del Viaje/Servicio"), blank=True, null=True)
    moneda = models.ForeignKey(Moneda, on_delete=models.PROTECT, verbose_name=_("Moneda"))
    subtotal = models.DecimalField(_("Subtotal"), max_digits=12, decimal_places=2, default=0)
    impuestos = models.DecimalField(_("Impuestos"), max_digits=12, decimal_places=2, default=0)
    total_cotizado = models.DecimalField(_("Total Cotizado"), max_digits=12, decimal_places=2, default=0)
    class EstadoCotizacion(models.TextChoices): BORRADOR = 'BOR', _('Borrador'); ENVIADA = 'ENV', _('Enviada al Cliente'); ACEPTADA = 'ACE', _('Aceptada por el Cliente'); RECHAZADA = 'REC', _('Rechazada por el Cliente'); VENCIDA = 'VEN', _('Vencida'); CONVERTIDA_A_VENTA = 'CNV', _('Convertida a Venta/Reserva')
    estado = models.CharField(_("Estado de la Cotización"), max_length=3, choices=EstadoCotizacion.choices, default=EstadoCotizacion.BORRADOR)
    notas_internas = models.TextField(_("Notas Internas"), blank=True, null=True)
    condiciones_comerciales = models.TextField(_("Condiciones Comerciales"), blank=True, null=True, help_text=_("Ej. políticas de cancelación, pagos, etc."))
    class Meta:
        verbose_name = _("Cotización")
        verbose_name_plural = _("Cotizaciones")
        ordering = ['-fecha_emision']
    def __str__(self): return f"Cotización {self.numero_cotizacion or self.id_cotizacion} para {self.cliente}"
    def save(self, *args, **kwargs):
        if not self.numero_cotizacion: self.numero_cotizacion = f"COT-{timezone.now().strftime('%Y%m%d')}-{Cotizacion.objects.count() + 1:04d}"
        self.total_cotizado = (self.subtotal or 0) + (self.impuestos or 0)
        super().save(*args, **kwargs)
    def calcular_totales_desde_items(self):
        subtotal_calculado = Decimal('0.00'); impuestos_calculados = Decimal('0.00')
        for item in self.items_cotizacion.all(): subtotal_calculado += item.precio_unitario * item.cantidad; impuestos_calculados += item.impuestos_item * item.cantidad
        self.subtotal = subtotal_calculado; self.impuestos = impuestos_calculados; self.total_cotizado = subtotal_calculado + impuestos_calculados
        self.save(update_fields=['subtotal', 'impuestos', 'total_cotizado'])

class ItemCotizacion(models.Model):
    id_item_cotizacion = models.AutoField(primary_key=True, verbose_name=_("ID Item Cotización"))
    cotizacion = models.ForeignKey(Cotizacion, related_name='items_cotizacion', on_delete=models.CASCADE, verbose_name=_("Cotización"))
    producto_servicio = models.ForeignKey(ProductoServicio, on_delete=models.PROTECT, verbose_name=_("Producto/Servicio"))
    descripcion_personalizada = models.CharField(_("Descripción Personalizada"), max_length=500, blank=True, null=True, help_text=_("Si se desea una descripción diferente a la del catálogo."))
    cantidad = models.PositiveIntegerField(_("Cantidad"), default=1)
    precio_unitario = models.DecimalField(_("Precio Unitario"), max_digits=12, decimal_places=2)
    impuestos_item = models.DecimalField(_("Impuestos por Item"), max_digits=12, decimal_places=2, default=0, help_text=_("Impuestos aplicables a este item específico por unidad."))
    subtotal_item = models.DecimalField(_("Subtotal Item"), max_digits=12, decimal_places=2, editable=False)
    total_item = models.DecimalField(_("Total Item"), max_digits=12, decimal_places=2, editable=False)
    class Meta:
        verbose_name = _("Item de Cotización")
        verbose_name_plural = _("Items de Cotización")
        ordering = ['id_item_cotizacion']
    def __str__(self): return f"{self.cantidad} x {self.producto_servicio.nombre} en {self.cotizacion.numero_cotizacion}"
    def save(self, *args, **kwargs):
        self.subtotal_item = self.precio_unitario * self.cantidad
        self.total_item = self.subtotal_item + (self.impuestos_item * self.cantidad)
        super().save(*args, **kwargs)

class PlanContable(models.Model):
    id_cuenta = models.AutoField(primary_key=True, verbose_name=_("ID Cuenta"))
    codigo_cuenta = models.CharField(_("Código de Cuenta"), max_length=30, unique=True, validators=[validar_no_vacio_o_espacios])
    nombre_cuenta = models.CharField(_("Nombre de la Cuenta"), max_length=100, validators=[validar_no_vacio_o_espacios])
    class TipoCuentaChoices(models.TextChoices): ACTIVO = 'AC', _('Activo'); PASIVO = 'PA', _('Pasivo'); PATRIMONIO = 'PT', _('Patrimonio'); INGRESO = 'IN', _('Ingreso'); GASTO = 'GA', _('Gasto/Costo'); CUENTA_ORDEN = 'CO', _('Cuenta de Orden')
    tipo_cuenta = models.CharField(_("Tipo de Cuenta"), max_length=2, choices=TipoCuentaChoices.choices)
    nivel = models.PositiveSmallIntegerField(_("Nivel Jerárquico"), default=1)
    cuenta_padre = models.ForeignKey('self', on_delete=models.SET_NULL, blank=True, null=True, related_name='subcuentas', verbose_name=_("Cuenta Padre"))
    permite_movimientos = models.BooleanField(_("Permite Movimientos"), default=True, help_text=_("Si es False, es una cuenta de agrupación."))
    class NaturalezaChoices(models.TextChoices): DEUDORA = 'D', _('Deudora'); ACREEDORA = 'H', _('Acreedora')
    naturaleza = models.CharField(_("Naturaleza"), max_length=1, choices=NaturalezaChoices.choices)
    descripcion = models.TextField(_("Descripción"), blank=True, null=True)
    class Meta:
        verbose_name = _("Cuenta Contable")
        verbose_name_plural = _("Plan de Cuentas")
        ordering = ['codigo_cuenta']
    def __str__(self): return f"{self.codigo_cuenta} - {self.nombre_cuenta}"

class AsientoContable(models.Model):
    id_asiento = models.AutoField(primary_key=True, verbose_name=_("ID Asiento"))
    numero_asiento = models.CharField(_("Número de Asiento"), max_length=20, unique=True, blank=True)
    fecha_contable = models.DateField(_("Fecha Contable"), default=timezone.now)
    descripcion_general = models.CharField(_("Descripción General"), max_length=255)
    class TipoAsientoChoices(models.TextChoices): DIARIO = 'DIA', _('Diario'); COMPRAS = 'COM', _('Compras'); VENTAS = 'VEN', _('Ventas'); NOMINA = 'NOM', _('Nómina'); APERTURA = 'APE', _('Apertura'); CIERRE = 'CIE', _('Cierre'); AJUSTE = 'AJU', _('Ajuste')
    tipo_asiento = models.CharField(_("Tipo de Asiento"), max_length=3, choices=TipoAsientoChoices.choices, default=TipoAsientoChoices.DIARIO)
    referencia_documento = models.CharField(_("Referencia Documento"), max_length=100, blank=True, null=True, help_text=_("Ej: Factura #, Reserva #"))
    class EstadoAsientoChoices(models.TextChoices): BORRADOR = 'BOR', _('Borrador'); CONTABILIZADO = 'CON', _('Contabilizado'); ANULADO = 'ANU', _('Anulado')
    estado = models.CharField(_("Estado"), max_length=3, choices=EstadoAsientoChoices.choices, default=EstadoAsientoChoices.BORRADOR)
    moneda = models.ForeignKey(Moneda, on_delete=models.PROTECT, verbose_name=_("Moneda del Asiento"))
    tasa_cambio_aplicada = models.DecimalField(_("Tasa de Cambio Aplicada"), max_digits=18, decimal_places=8, default=1.00, help_text=_("Respecto a la moneda local, si aplica."))
    fecha_creacion = models.DateTimeField(_("Fecha de Creación"), auto_now_add=True)
    total_debe = models.DecimalField(_("Total Debe"), max_digits=15, decimal_places=2, default=0, editable=False)
    total_haber = models.DecimalField(_("Total Haber"), max_digits=15, decimal_places=2, default=0, editable=False)
    class Meta:
        verbose_name = _("Asiento Contable")
        verbose_name_plural = _("Asientos Contables")
        ordering = ['-fecha_contable', '-numero_asiento']
    def __str__(self): return f"Asiento {self.numero_asiento or self.id_asiento} ({self.fecha_contable})"
    def save(self, *args, **kwargs):
        if not self.numero_asiento: self.numero_asiento = f"ASI-{self.fecha_contable.strftime('%Y%m%d')}-{AsientoContable.objects.count() + 1:04d}"
        super().save(*args, **kwargs)
    def calcular_totales(self):
        detalles = self.detalles_asiento.all()
        self.total_debe = sum(d.debe for d in detalles); self.total_haber = sum(d.haber for d in detalles)
        self.save(update_fields=['total_debe', 'total_haber'])
    def esta_cuadrado(self): return self.total_debe == self.total_haber
    esta_cuadrado.boolean = True; esta_cuadrado.short_description = _("¿Cuadrado?")

class DetalleAsiento(models.Model):
    id_detalle_asiento = models.AutoField(primary_key=True, verbose_name=_("ID Detalle Asiento"))
    asiento = models.ForeignKey(AsientoContable, related_name='detalles_asiento', on_delete=models.CASCADE, verbose_name=_("Asiento Contable"))
    linea = models.PositiveSmallIntegerField(_("Línea"), help_text=_("Número de línea dentro del asiento."))
    cuenta_contable = models.ForeignKey(PlanContable, on_delete=models.PROTECT, verbose_name=_("Cuenta Contable"), limit_choices_to={'permite_movimientos': True})
    debe = models.DecimalField(_("Debe"), max_digits=15, decimal_places=2, default=0)
    haber = models.DecimalField(_("Haber"), max_digits=15, decimal_places=2, default=0)
    descripcion_linea = models.CharField(_("Descripción de la Línea"), max_length=255, blank=True, null=True)
    class Meta:
        verbose_name = _("Detalle de Asiento")
        verbose_name_plural = _("Detalles de Asientos")
        ordering = ['asiento', 'linea']
        unique_together = ('asiento', 'linea')
    def __str__(self): return f"Línea {self.linea} de Asiento {self.asiento.numero_asiento}: {self.cuenta_contable.codigo_cuenta} D:{self.debe} H:{self.haber}"
    def clean(self):
        if self.debe < 0 or self.haber < 0: raise ValidationError(_("Los montos de Debe y Haber no pueden ser negativos."))
        if self.debe > 0 and self.haber > 0: raise ValidationError(_("Una línea no puede tener movimientos en Debe y Haber simultáneamente."))
        if self.debe == 0 and self.haber == 0: raise ValidationError(_("Debe registrar un movimiento en Debe o en Haber."))
        if not self.cuenta_contable.permite_movimientos: raise ValidationError(_("La cuenta contable seleccionada no permite movimientos directos."))

class Venta(models.Model):
    id_venta = models.AutoField(primary_key=True, verbose_name=_("ID Venta/Reserva"))
    localizador = models.CharField(_("Localizador/PNR"), max_length=20, unique=True, blank=True, help_text=_("Código único de la reserva o localizador."))
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, verbose_name=_("Cliente (Pagador)"))
    pasajeros = models.ManyToManyField('Pasajero', related_name='ventas', verbose_name=_("Pasajeros"))
    cotizacion_origen = models.OneToOneField(Cotizacion, on_delete=models.SET_NULL, blank=True, null=True, verbose_name=_("Cotización de Origen"))
    fecha_venta = models.DateTimeField(_("Fecha de Venta/Reserva"), default=timezone.now)
    descripcion_general = models.TextField(_("Descripción General de la Venta"), blank=True, null=True)
    moneda = models.ForeignKey(Moneda, on_delete=models.PROTECT, verbose_name=_("Moneda"))
    subtotal = models.DecimalField(_("Subtotal"), max_digits=12, decimal_places=2, default=0)
    impuestos = models.DecimalField(_("Impuestos"), max_digits=12, decimal_places=2, default=0)
    total_venta = models.DecimalField(_("Total Venta"), max_digits=12, decimal_places=2, default=0, editable=False)
    monto_pagado = models.DecimalField(_("Monto Pagado"), max_digits=12, decimal_places=2, default=0)
    saldo_pendiente = models.DecimalField(_("Saldo Pendiente"), max_digits=12, decimal_places=2, default=0, editable=False)
    
    class EstadoVenta(models.TextChoices):
        PENDIENTE_PAGO = 'PEN', _('Pendiente de Pago')
        PAGADA_PARCIAL = 'PAR', _('Pagada Parcialmente')
        PAGADA_TOTAL = 'PAG', _('Pagada Totalmente')
        CONFIRMADA = 'CNF', _('Confirmada (Servicios OK)')
        EN_PROCESO_VIAJE = 'VIA', _('En Proceso/Viaje')
        COMPLETADA = 'COM', _('Completada')
        CANCELADA = 'CAN', _('Cancelada')

    estado = models.CharField(_("Estado de la Venta/Reserva"), max_length=3, choices=EstadoVenta.choices, default=EstadoVenta.PENDIENTE_PAGO)
    class TipoVenta(models.TextChoices):
        B2C = 'B2C', _('B2C (Ocio)')
        B2B = 'B2B', _('B2B (Corporativo)')
        MICE = 'MICE', _('MICE / Eventos')
        PAQUETE = 'PKG', _('Paquete')
        CIRCUITO = 'CIR', _('Circuito')
        TAILOR = 'TLD', _('Viaje a Medida')
        SEGURO = 'SEG', _('Solo Seguro')
        OTRO = 'OTR', _('Otro')
    tipo_venta = models.CharField(_("Tipo de Venta"), max_length=4, choices=TipoVenta.choices, default=TipoVenta.B2C, db_index=True)
    class CanalOrigen(models.TextChoices):
        ADMIN = 'ADM', _('Admin')
        IMPORTACION = 'IMP', _('Importación')
        API = 'API', _('API')
        WEBFORM = 'WEB', _('Formulario Web')
        MIGRACION = 'MIG', _('Migración')
        OTRO = 'OTR', _('Otro')
    canal_origen = models.CharField(_("Canal de Origen"), max_length=3, choices=CanalOrigen.choices, default=CanalOrigen.ADMIN, db_index=True)
    margen_estimado = models.DecimalField(_("Margen Estimado"), max_digits=12, decimal_places=2, blank=True, null=True, help_text=_("Precio venta - costo neto estimado (informativo)."))
    co2_estimado_kg = models.DecimalField(_("Emisiones CO₂ Estimadas (kg)"), max_digits=12, decimal_places=2, blank=True, null=True, help_text=_("Estimación agregada de la huella de carbono."))
    asiento_contable_venta = models.ForeignKey(AsientoContable, related_name='ventas_asociadas', on_delete=models.SET_NULL, blank=True, null=True, verbose_name=_("Asiento Contable de Venta"))
    factura = models.ForeignKey('Factura', on_delete=models.SET_NULL, blank=True, null=True, related_name='ventas', verbose_name=_("Factura Asociada"))
    notas = models.TextField(_("Notas de la Venta"), blank=True, null=True)
    puntos_fidelidad_asignados = models.BooleanField(_("Puntos Fidelidad Asignados"), default=False, editable=False,
        help_text=_("Evita otorgar puntos duplicados cuando la venta pasa a completada/pagada."))

    class Meta:
        verbose_name = _("Venta / Reserva")
        verbose_name_plural = _("Ventas / Reservas")
        ordering = ['-fecha_venta']

    def __str__(self):
        return f"Venta {self.localizador or self.id_venta} a {self.cliente}"

    def save(self, *args, **kwargs):
        if not self.localizador:
            self.localizador = f"VTA-{self.fecha_venta.strftime('%Y%m%d')}-{Venta.objects.count() + 1:04d}"
        # Para consistencia con recalcular_finanzas, si ya existen fees y pagos confirmados recalculamos usando mismo criterio
        if self.pk:
            from django.db.models import Sum
            subtotal_items = sum(iv.total_item_venta for iv in self.items_venta.all()) if self.items_venta.exists() else Decimal('0.00')
            fees_total = self.fees_venta.aggregate(s=Sum('monto'))['s'] or Decimal('0.00') if hasattr(self, 'fees_venta') else Decimal('0.00')
            pagos_confirmados = self.pagos_venta.filter(confirmado=True).aggregate(s=Sum('monto'))['s'] or Decimal('0.00') if hasattr(self, 'pagos_venta') else Decimal('0.00')
            # Subtotal refleja items (con impuestos por item ya incorporados en total_item_venta)
            self.subtotal = subtotal_items
            self.total_venta = subtotal_items + (self.impuestos or 0) + fees_total
            self.saldo_pendiente = self.total_venta - pagos_confirmados
        else:
            self.total_venta = (self.subtotal or 0) + (self.impuestos or 0)
            self.saldo_pendiente = self.total_venta - (self.monto_pagado or 0)
        # Actualizar estado según pagos SOLO si el estado actual es uno de los financieros base
        estados_financieros_base = {Venta.EstadoVenta.PENDIENTE_PAGO, Venta.EstadoVenta.PAGADA_PARCIAL, Venta.EstadoVenta.PAGADA_TOTAL}
        if self.estado in estados_financieros_base and self.total_venta > 0:
            if self.saldo_pendiente <= 0:
                self.estado = Venta.EstadoVenta.PAGADA_TOTAL
            elif 0 < self.saldo_pendiente < self.total_venta:
                self.estado = Venta.EstadoVenta.PAGADA_PARCIAL
        super().save(*args, **kwargs)
        # Evaluar puntos luego de guardar
        self._evaluar_otorgar_puntos(contexto="save")

    def _evaluar_otorgar_puntos(self, contexto: str):
        """Otorga puntos de fidelidad si la venta está totalmente pagada (saldo <= 0)
        o alcanza un estado avanzado (COMPLETADA o PAGADA_TOTAL) y aún no se otorgaron.
        """
        try:
            logger.debug(
                "[Venta %s] Evaluación puntos (%s): estado=%s total=%s saldo=%s flag=%s",
                self.pk, contexto, self.estado, self.total_venta, self.saldo_pendiente, self.puntos_fidelidad_asignados
            )
            # (debug prints removidos)
            if not self.puntos_fidelidad_asignados and (
                self.saldo_pendiente <= 0 or self.estado in (Venta.EstadoVenta.COMPLETADA, Venta.EstadoVenta.PAGADA_TOTAL)
            ):
                puntos_ganados = int(self.total_venta / 10)
                # (debug prints removidos)
                if puntos_ganados > 0:
                    logger.debug("[Venta %s] Otorgando %s puntos (contexto=%s)", self.pk, puntos_ganados, contexto)
                    self.cliente.puntos_fidelidad += puntos_ganados
                    self.cliente.calcular_cliente_frecuente()
                    self.cliente.save(update_fields=['puntos_fidelidad', 'es_cliente_frecuente'])
                    self.puntos_fidelidad_asignados = True
                    super(Venta, self).save(update_fields=['puntos_fidelidad_asignados'])
        except Exception as e:
            logger.exception("Error otorgando puntos en Venta %s: %s", self.pk, e)

    def recalcular_finanzas(self):
        from django.db.models import Sum
        subtotal_items = sum(iv.total_item_venta for iv in self.items_venta.all()) if self.items_venta.exists() else Decimal('0.00')
        fees_total = self.fees_venta.aggregate(s=Sum('monto'))['s'] or Decimal('0.00') if hasattr(self, 'fees_venta') else Decimal('0.00')
        pagos_confirmados = self.pagos_venta.filter(confirmado=True).aggregate(s=Sum('monto'))['s'] or Decimal('0.00') if hasattr(self, 'pagos_venta') else Decimal('0.00')
        self.subtotal = subtotal_items
        self.total_venta = subtotal_items + (self.impuestos or 0) + fees_total
        # Actualizar monto_pagado y saldo
        self.monto_pagado = pagos_confirmados
        self.saldo_pendiente = self.total_venta - self.monto_pagado
        # No llamar recursivamente save completo para evitar recalculo doble de puntos; actualizamos campos y estado transicional
        campos_update = ['subtotal', 'total_venta', 'monto_pagado', 'saldo_pendiente']
        estado_original = self.estado
        estados_financieros_base = {Venta.EstadoVenta.PENDIENTE_PAGO, Venta.EstadoVenta.PAGADA_PARCIAL, Venta.EstadoVenta.PAGADA_TOTAL}
        if self.estado in estados_financieros_base and self.total_venta > 0:
            if self.saldo_pendiente <= 0:
                self.estado = Venta.EstadoVenta.PAGADA_TOTAL
            elif 0 < self.saldo_pendiente < self.total_venta:
                self.estado = Venta.EstadoVenta.PAGADA_PARCIAL
        if self.estado != estado_original:
            campos_update.append('estado')
        super().save(update_fields=campos_update)
        # Evaluar otorgamiento de puntos tras recálculo
        self._evaluar_otorgar_puntos(contexto="recalcular_finanzas")

class ItemVenta(models.Model):
    id_item_venta = models.AutoField(primary_key=True, verbose_name=_("ID Item Venta"))
    venta = models.ForeignKey(Venta, related_name='items_venta', on_delete=models.CASCADE, verbose_name=_("Venta"))
    producto_servicio = models.ForeignKey(ProductoServicio, on_delete=models.PROTECT, verbose_name=_("Producto/Servicio"))
    descripcion_personalizada = models.CharField(_("Descripción Personalizada"), max_length=500, blank=True, null=True)
    cantidad = models.PositiveIntegerField(_("Cantidad"), default=1)
    precio_unitario_venta = models.DecimalField(_("Precio Unitario de Venta"), max_digits=12, decimal_places=2)
    costo_unitario_referencial = models.DecimalField(_("Costo Unitario Referencial"), max_digits=12, decimal_places=2, blank=True, null=True)
    impuestos_item_venta = models.DecimalField(_("Impuestos por Item"), max_digits=12, decimal_places=2, default=0)
    subtotal_item_venta = models.DecimalField(_("Subtotal Item"), max_digits=12, decimal_places=2, editable=False)
    total_item_venta = models.DecimalField(_("Total Item"), max_digits=12, decimal_places=2, editable=False)
    fecha_inicio_servicio = models.DateTimeField(_("Fecha Inicio Servicio"), blank=True, null=True)
    fecha_fin_servicio = models.DateTimeField(_("Fecha Fin Servicio"), blank=True, null=True)
    codigo_reserva_proveedor = models.CharField(_("Código Reserva Proveedor (PNR, Localizador)"), max_length=50, blank=True, null=True)
    proveedor_servicio = models.ForeignKey(Proveedor, on_delete=models.SET_NULL, blank=True, null=True, verbose_name=_("Proveedor del Servicio"))
    class EstadoItemVenta(models.TextChoices): PENDIENTE_CONFIRMACION = 'PCO', _('Pendiente Confirmación Proveedor'); CONFIRMADO = 'CNF', _('Confirmado por Proveedor'); CANCELADO_PROVEEDOR = 'CAP', _('Cancelado por Proveedor'); CANCELADO_CLIENTE = 'CAC', _('Cancelado por Cliente'); UTILIZADO = 'UTI', _('Utilizado/Completado')
    estado_item = models.CharField(_("Estado del Item/Servicio"), max_length=3, choices=EstadoItemVenta.choices, default=EstadoItemVenta.PENDIENTE_CONFIRMACION)
    notas_item = models.TextField(_("Notas del Item"), blank=True, null=True)
    class Meta:
        verbose_name = _("Item de Venta/Reserva")
        verbose_name_plural = _("Items de Venta/Reserva")
    def __str__(self): return f"{self.cantidad} x {self.producto_servicio.nombre} en Venta {self.venta.localizador}"
    def save(self, *args, **kwargs):
        self.subtotal_item_venta = self.precio_unitario_venta * self.cantidad
        self.total_item_venta = self.subtotal_item_venta + (self.impuestos_item_venta * self.cantidad)
        super().save(*args, **kwargs)
        # Recalcular finanzas de la venta relacionada
        if self.venta_id:
            self.venta.recalcular_finanzas()

class SegmentoVuelo(models.Model):
    id_segmento_vuelo = models.AutoField(primary_key=True, verbose_name=_("ID Segmento Vuelo"))
    venta = models.ForeignKey(Venta, related_name='segmentos_vuelo', on_delete=models.CASCADE, verbose_name=_("Venta"))
    origen = models.ForeignKey(Ciudad, related_name='segmentos_salida', on_delete=models.PROTECT, verbose_name=_("Ciudad Origen"))
    destino = models.ForeignKey(Ciudad, related_name='segmentos_llegada', on_delete=models.PROTECT, verbose_name=_("Ciudad Destino"))
    aerolinea = models.CharField(_("Aerolínea"), max_length=80, blank=True, null=True)
    numero_vuelo = models.CharField(_("Número de Vuelo"), max_length=20, blank=True, null=True)
    fecha_salida = models.DateTimeField(_("Fecha/Hora Salida"), blank=True, null=True)
    fecha_llegada = models.DateTimeField(_("Fecha/Hora Llegada"), blank=True, null=True)
    clase_reserva = models.CharField(_("Clase"), max_length=5, blank=True, null=True)
    cabina = models.CharField(_("Cabina"), max_length=20, blank=True, null=True, help_text=_("Ej: Economy, Business, First"))
    notas = models.TextField(_("Notas"), blank=True, null=True)
    class Meta:
        verbose_name = _("Segmento de Vuelo")
        verbose_name_plural = _("Segmentos de Vuelo")
        ordering = ['fecha_salida']
    def __str__(self): return f"{self.origen} → {self.destino} {self.numero_vuelo or ''}".strip()

class AlojamientoReserva(models.Model):
    id_alojamiento_reserva = models.AutoField(primary_key=True, verbose_name=_("ID Alojamiento"))
    venta = models.ForeignKey(Venta, related_name='alojamientos', on_delete=models.CASCADE, verbose_name=_("Venta"))
    proveedor = models.ForeignKey(Proveedor, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("Proveedor"))
    ciudad = models.ForeignKey(Ciudad, on_delete=models.PROTECT, verbose_name=_("Ciudad"))
    nombre_establecimiento = models.CharField(_("Nombre Establecimiento"), max_length=150)
    check_in = models.DateField(_("Check In"), blank=True, null=True)
    check_out = models.DateField(_("Check Out"), blank=True, null=True)
    regimen_alimentacion = models.CharField(_("Régimen Alimentación"), max_length=30, blank=True, null=True, help_text=_("Ej: Desayuno, Media Pensión, Todo Incluido"))
    habitaciones = models.PositiveSmallIntegerField(_("Habitaciones"), default=1)
    notas = models.TextField(_("Notas"), blank=True, null=True)
    class Meta:
        verbose_name = _("Alojamiento (Reserva)")
        verbose_name_plural = _("Alojamientos (Reservas)")
        ordering = ['check_in']
    def __str__(self): return f"{self.nombre_establecimiento} ({self.ciudad})"

class TrasladoServicio(models.Model):
    id_traslado_servicio = models.AutoField(primary_key=True, verbose_name=_("ID Traslado"))
    venta = models.ForeignKey(Venta, related_name='traslados', on_delete=models.CASCADE, verbose_name=_("Venta"))
    class TipoTraslado(models.TextChoices):
        ARRIBO = 'ARR', _('Arribo / Llegada')
        SALIDA = 'DEP', _('Salida')
        INTERNO = 'INT', _('Interno')
    tipo_traslado = models.CharField(_("Tipo Traslado"), max_length=3, choices=TipoTraslado.choices, default=TipoTraslado.ARRIBO)
    origen = models.CharField(_("Origen"), max_length=150, blank=True, null=True)
    destino = models.CharField(_("Destino"), max_length=150, blank=True, null=True)
    fecha_hora = models.DateTimeField(_("Fecha/Hora"), blank=True, null=True)
    proveedor = models.ForeignKey(Proveedor, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("Proveedor"))
    pasajeros = models.PositiveSmallIntegerField(_("Pasajeros"), default=1)
    notas = models.TextField(_("Notas"), blank=True, null=True)
    class Meta:
        verbose_name = _("Traslado")
        verbose_name_plural = _("Traslados")
        ordering = ['fecha_hora']
    def __str__(self): return f"{self.get_tipo_traslado_display()} {self.origen or ''}→{self.destino or ''}".strip()

class ActividadServicio(models.Model):
    id_actividad_servicio = models.AutoField(primary_key=True, verbose_name=_("ID Actividad"))
    venta = models.ForeignKey(Venta, related_name='actividades', on_delete=models.CASCADE, verbose_name=_("Venta"))
    nombre = models.CharField(_("Nombre Actividad"), max_length=150)
    fecha = models.DateField(_("Fecha"), blank=True, null=True)
    duracion_horas = models.DecimalField(_("Duración (horas)"), max_digits=5, decimal_places=2, blank=True, null=True)
    incluye = models.TextField(_("Incluye"), blank=True, null=True)
    no_incluye = models.TextField(_("No Incluye"), blank=True, null=True)
    proveedor = models.ForeignKey(Proveedor, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("Proveedor"))
    notas = models.TextField(_("Notas"), blank=True, null=True)
    class Meta:
        verbose_name = _("Actividad / Excursión")
        verbose_name_plural = _("Actividades / Excursiones")
        ordering = ['fecha', 'nombre']
    def __str__(self): return self.nombre

class FeeVenta(models.Model):
    id_fee_venta = models.AutoField(primary_key=True, verbose_name=_("ID Fee"))
    venta = models.ForeignKey(Venta, related_name='fees_venta', on_delete=models.CASCADE, verbose_name=_("Venta"))
    class TipoFee(models.TextChoices):
        EMISION = 'EMI', _('Emisión')
        CAMBIO = 'CAM', _('Cambio / Exchange')
        GESTION = 'GST', _('Gestión')
        URGENTE = 'URG', _('Urgente')
        OTRO = 'OTR', _('Otro')
    tipo_fee = models.CharField(_("Tipo Fee"), max_length=3, choices=TipoFee.choices, default=TipoFee.GESTION)
    descripcion = models.CharField(_("Descripción"), max_length=200, blank=True, null=True)
    monto = models.DecimalField(_("Monto"), max_digits=12, decimal_places=2)
    moneda = models.ForeignKey(Moneda, on_delete=models.PROTECT, verbose_name=_("Moneda"))
    es_comision_agencia = models.BooleanField(_("Es Comisión Agencia"), default=True)
    taxable = models.BooleanField(_("Sujeto a Impuestos"), default=False)
    creado = models.DateTimeField(auto_now_add=True)
    class Meta:
        verbose_name = _("Fee de Venta")
        verbose_name_plural = _("Fees de Venta")
        ordering = ['-creado']
    def __str__(self): return f"{self.get_tipo_fee_display()} {self.monto} {self.moneda.codigo_iso}"
    # El recálculo ahora se maneja vía signal post_save para evitar dobles ejecuciones.

class PagoVenta(models.Model):
    id_pago_venta = models.AutoField(primary_key=True, verbose_name=_("ID Pago"))
    venta = models.ForeignKey(Venta, related_name='pagos_venta', on_delete=models.CASCADE, verbose_name=_("Venta"))
    fecha_pago = models.DateTimeField(_("Fecha Pago"), default=timezone.now)
    monto = models.DecimalField(_("Monto"), max_digits=12, decimal_places=2)
    moneda = models.ForeignKey(Moneda, on_delete=models.PROTECT, verbose_name=_("Moneda"))
    class MetodoPago(models.TextChoices):
        EFECTIVO = 'EFE', _('Efectivo')
        TARJETA = 'TAR', _('Tarjeta')
        TRANSFERENCIA = 'TRF', _('Transferencia')
        ZELLE = 'ZEL', _('Zelle')
        PAYPAL = 'PPL', _('PayPal')
        OTRO = 'OTR', _('Otro')
    metodo = models.CharField(_("Método"), max_length=3, choices=MetodoPago.choices, default=MetodoPago.TRANSFERENCIA)
    referencia = models.CharField(_("Referencia"), max_length=100, blank=True, null=True)
    confirmado = models.BooleanField(_("Confirmado"), default=True)
    notas = models.TextField(_("Notas"), blank=True, null=True)
    creado = models.DateTimeField(auto_now_add=True)
    class Meta:
        verbose_name = _("Pago de Venta")
        verbose_name_plural = _("Pagos de Venta")
        ordering = ['-fecha_pago']
    def __str__(self): return f"Pago {self.monto} {self.moneda.codigo_iso} ({self.get_metodo_display()})"
    # El recálculo ahora se maneja vía signal post_save para evitar dobles ejecuciones.

class Factura(models.Model):
    id_factura = models.AutoField(primary_key=True, verbose_name=_("ID Factura"))
    numero_factura = models.CharField(_("Número de Factura"), max_length=50, unique=True, blank=True, help_text=_("Puede ser un correlativo fiscal o interno."))
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, verbose_name=_("Cliente"))
    fecha_emision = models.DateField(_("Fecha de Emisión"), default=timezone.now)
    fecha_vencimiento = models.DateField(_("Fecha de Vencimiento"), blank=True, null=True)
    moneda = models.ForeignKey(Moneda, on_delete=models.PROTECT, verbose_name=_("Moneda"))
    subtotal = models.DecimalField(_("Subtotal"), max_digits=12, decimal_places=2, default=0)
    monto_impuestos = models.DecimalField(_("Monto Impuestos"), max_digits=12, decimal_places=2, default=0)
    monto_total = models.DecimalField(_("Monto Total"), max_digits=12, decimal_places=2, default=0, editable=False)
    saldo_pendiente = models.DecimalField(_("Saldo Pendiente"), max_digits=12, decimal_places=2, default=0, editable=False)

    class EstadoFactura(models.TextChoices):
        BORRADOR = 'BOR', _('Borrador')
        EMITIDA = 'EMI', _('Emitida (Pendiente de Pago)')
        PAGADA_PARCIAL = 'PAR', _('Pagada Parcialmente')
        PAGADA_TOTAL = 'PAG', _('Pagada Totalmente')
        VENCIDA = 'VEN', _('Vencida')
        ANULADA = 'ANU', _('Anulada')

    estado = models.CharField(_("Estado de la Factura"), max_length=3, choices=EstadoFactura.choices, default=EstadoFactura.BORRADOR)
    asiento_contable_factura = models.ForeignKey(AsientoContable, related_name='facturas_asociadas', on_delete=models.SET_NULL, blank=True, null=True, verbose_name=_("Asiento Contable de Factura"))
    notas = models.TextField(_("Notas de la Factura"), blank=True, null=True)

    class Meta:
        verbose_name = _("Factura de Cliente")
        verbose_name_plural = _("Facturas de Clientes")
        ordering = ['-fecha_emision', '-numero_factura']

    def __str__(self):
        return f"Factura {self.numero_factura or self.id_factura} a {self.cliente}"

    def save(self, *args, **kwargs):
        if not self.numero_factura:
            ultimo_numero = Factura.objects.all().order_by('id_factura').last()
            nuevo_id = (ultimo_numero.id_factura + 1) if ultimo_numero else 1
            self.numero_factura = f"FAC-{self.fecha_emision.strftime('%Y')}-{nuevo_id:05d}"
        
        if self.pk:
            self.recalcular_totales()
        else:
            self.monto_total = (self.subtotal or 0) + (self.monto_impuestos or 0)
        
        if not self.pk:
            self.saldo_pendiente = self.monto_total
        
        super().save(*args, **kwargs)

    def recalcular_totales(self):
        subtotal_calculado = Decimal('0.00')
        impuestos_calculados = Decimal('0.00')
        
        for venta in self.ventas.all():
            subtotal_calculado += venta.subtotal
            impuestos_calculados += venta.impuestos
            
        self.subtotal = subtotal_calculado
        self.monto_impuestos = impuestos_calculados
        self.monto_total = self.subtotal + self.monto_impuestos
        self.save(update_fields=['subtotal', 'monto_impuestos', 'monto_total'])

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
    def __str__(self): return f"{self.cantidad} x {self.descripcion} en Factura {self.factura.numero_factura}"
    def save(self, *args, **kwargs): self.subtotal_item = self.precio_unitario * self.cantidad; super().save(*args, **kwargs)

class BoletoImportado(models.Model):
    id_boleto_importado = models.AutoField(primary_key=True, verbose_name=_("ID Boleto Importado"))
    archivo_boleto = models.FileField(
        _("Archivo del Boleto (.pdf, .txt, .eml)"),
        upload_to='boletos_importados/%Y/%m/',
        help_text=_("Suba el archivo del boleto en formato PDF, TXT o EML.")
    )
    fecha_subida = models.DateTimeField(_("Fecha de Subida"), auto_now_add=True)
    
    class FormatoDetectado(models.TextChoices):
        PDF_KIU = 'PDF_KIU', _('PDF (KIU)')
        PDF_SABRE = 'PDF_SAB', _('PDF (Sabre)')
        PDF_AMADEUS = 'PDF_AMA', _('PDF (Amadeus)')
        TXT_KIU = 'TXT_KIU', _('TXT (KIU)')
        TXT_SABRE = 'TXT_SAB', _('TXT (Sabre)')
        TXT_AMADEUS = 'TXT_AMA', _('TXT (Amadeus)')
        EML_KIU = 'EML_KIU', _('EML (KIU)') 
        EML_GENERAL = 'EML_GEN', _('EML (General)')
        OTRO = 'OTR', _('Otro/Desconocido')
        ERROR_FORMATO = 'ERR', _('Error de Formato')

    formato_detectado = models.CharField(
        _("Formato Detectado"),
        max_length=10,
        choices=FormatoDetectado.choices,
        default=FormatoDetectado.OTRO,
        blank=True
    )
    
    datos_parseados = models.JSONField(_("Datos Parseados"), blank=True, null=True, help_text=_("Información extraída del boleto en formato JSON."))
    
    class EstadoParseo(models.TextChoices):
        PENDIENTE = 'PEN', _('Pendiente de Parseo')
        EN_PROCESO = 'PRO', _('En Proceso')
        COMPLETADO = 'COM', _('Parseo Completado')
        ERROR_PARSEO = 'ERR', _('Error en Parseo')
        NO_APLICA = 'NAP', _('No Aplica Parseo')

    estado_parseo = models.CharField(
        _("Estado del Parseo"),
        max_length=3,
        choices=EstadoParseo.choices,
        default=EstadoParseo.PENDIENTE,
    )
    log_parseo = models.TextField(_("Log del Parseo"), blank=True, null=True)
    
    numero_boleto = models.CharField(_("Número de Boleto"), max_length=50, blank=True, null=True)
    nombre_pasajero_completo = models.CharField(_("Nombre Completo Pasajero (Original)"), max_length=150, blank=True, null=True)
    nombre_pasajero_procesado = models.CharField(_("Nombre Pasajero (Procesado)"), max_length=150, blank=True, null=True)
    ruta_vuelo = models.TextField(_("Ruta del Vuelo (Itinerario)"), blank=True, null=True) 
    fecha_emision_boleto = models.DateField(_("Fecha de Emisión del Boleto"), blank=True, null=True)
    aerolinea_emisora = models.CharField(_("Aerolínea Emisora"), max_length=100, blank=True, null=True)
    direccion_aerolinea = models.TextField(_("Dirección Aerolínea"), blank=True, null=True)
    agente_emisor = models.CharField(_("Agente Emisor"), max_length=100, blank=True, null=True)
    foid_pasajero = models.CharField(_("FOID/D.Identidad Pasajero"), max_length=50, blank=True, null=True)
    localizador_pnr = models.CharField(_("Localizador (PNR)"), max_length=10, blank=True, null=True)
    tarifa_base = models.DecimalField(_("Tarifa Base"), max_digits=10, decimal_places=2, blank=True, null=True)
    impuestos_descripcion = models.TextField(_("Descripción Impuestos"), blank=True, null=True)
    impuestos_total_calculado = models.DecimalField(_("Total Impuestos (Calculado)"), max_digits=10, decimal_places=2, blank=True, null=True)
    total_boleto = models.DecimalField(_("Total del Boleto"), max_digits=10, decimal_places=2, blank=True, null=True)
    # Campos financieros adicionales para edición manual / ajustes
    exchange_monto = models.DecimalField(_("Exchange"), max_digits=10, decimal_places=2, blank=True, null=True, help_text=_("Monto de exchange o diferencial de cambio asociado al boleto."))
    void_monto = models.DecimalField(_("Void / Penalidad"), max_digits=10, decimal_places=2, blank=True, null=True, help_text=_("Monto asociado a VOID (penalidad / reembolso negativo)."))
    fee_servicio = models.DecimalField(_("Fee de Servicio"), max_digits=10, decimal_places=2, blank=True, null=True, help_text=_("Fee cobrado por la agencia por gestión del boleto."))
    igtf_monto = models.DecimalField(_("IGTF"), max_digits=10, decimal_places=2, blank=True, null=True, help_text=_("Impuesto a las Grandes Transacciones Financieras u otras retenciones locales."))
    comision_agencia = models.DecimalField(_("Comisión Agencia"), max_digits=10, decimal_places=2, blank=True, null=True, help_text=_("Comisión propia de la agencia respecto al boleto."))
    
    venta_asociada = models.OneToOneField('Venta', on_delete=models.SET_NULL, blank=True, null=True, related_name='boleto_importado', verbose_name=_("Venta/Reserva Asociada"))
    archivo_pdf_generado = models.FileField(_("PDF Unificado Generado"), upload_to='boletos_generados/%Y/%m/', blank=True, null=True, help_text=_("El archivo PDF del boleto unificado, generado automáticamente."))

    class Meta:
        verbose_name = _("Boleto Importado")
        verbose_name_plural = _("Boletos Importados")
        ordering = ['-fecha_subida']

    def __str__(self):
        return f"Boleto {self.id_boleto_importado} ({self.archivo_boleto.name if self.archivo_boleto else 'N/A'})"

    def parsear_boleto(self):
        logger.debug("Ejecutando parsear_boleto para boleto ID %s", self.id_boleto_importado)
        log_parseo_list = [str(_("Iniciando proceso unificado de parseo..."))]
        
        try:
            if self.archivo_boleto:
                self.estado_parseo = BoletoImportado.EstadoParseo.EN_PROCESO
                plain_text, html_text = "", ""
                file_extension = self.archivo_boleto.name.split('.')[-1].lower()
                with self.archivo_boleto.open('rb') as f:
                    file_bytes = f.read()

                if file_extension == 'pdf':
                    log_parseo_list.append(str(_("Procesando archivo PDF...")))
                    # La extracción de texto se delega al parser específico
                    plain_text = "" # Se deja vacío para que el parser de PDF trabaje
                    extracted_data = ticket_parser.extract_data_from_text(plain_text, html_text, self.archivo_boleto.path)
                else:
                    if file_extension == 'txt':
                        log_parseo_list.append(str(_("Procesando archivo TXT...")))
                        plain_text = file_bytes.decode('utf-8', errors='replace')
                    elif file_extension == 'eml':
                        log_parseo_list.append(str(_("Procesando archivo EML...")))
                        ep = EmlParser(include_raw_body=True, include_attachment_data=False)
                        parsed_eml = ep.decode_email_bytes(file_bytes)
                        if 'body' in parsed_eml:
                            for part in parsed_eml['body']:
                                if part.get('content_type') == 'text/html' and part.get('content'):
                                    html_text = part['content']
                                    break
                        soup = BeautifulSoup(html_text if html_text else parsed_eml.get('raw_body', ''), 'html.parser')
                        for element in soup.find_all(['p', 'div', 'br', 'tr', 'h1', 'h2', 'h3']):
                            element.append('\n')
                        plain_text = soup.get_text(separator=' ', strip=True)
                        if not plain_text: raise ValueError("No se pudo extraer contenido textual útil del EML.")
                    else:
                        raise ValueError(f"Formato de archivo no soportado: {file_extension}")
                    
                    extracted_data = ticket_parser.extract_data_from_text(plain_text, html_text)
                log_parseo_list.append(str(_("Datos extraídos del boleto.")))
                
                self.datos_parseados = extracted_data
                
                # Mapeo de campos compatible con KIU y Sabre PDF
                self.numero_boleto = extracted_data.get('numero_boleto') or extracted_data.get('NUMERO_DE_BOLETO', '').replace('-', '').strip()
                self.fecha_emision_boleto = ticket_parser.string_a_fecha(extracted_data.get('fecha_emision') or extracted_data.get('FECHA_DE_EMISION'))
                self.agente_emisor = ticket_parser._clean_value(extracted_data.get('agente_emisor') or extracted_data.get('AGENTE_EMISOR'))
                self.nombre_pasajero_completo = ticket_parser._clean_value(extracted_data.get('preparado_para') or extracted_data.get('NOMBRE_DEL_PASAJERO'))
                self.nombre_pasajero_procesado = ticket_parser._clean_value(extracted_data.get('preparado_para') or extracted_data.get('SOLO_NOMBRE_PASAJERO'))
                self.foid_pasajero = ticket_parser._clean_value(extracted_data.get('numero_cliente') or extracted_data.get('CODIGO_IDENTIFICACION'))
                self.localizador_pnr = ticket_parser._clean_value(extracted_data.get('codigo_reservacion') or extracted_data.get('SOLO_CODIGO_RESERVA'))
                self.aerolinea_emisora = ticket_parser._clean_value(extracted_data.get('aerolinea_emisora') or extracted_data.get('NOMBRE_AEROLINEA'))
                self.direccion_aerolinea = ticket_parser._clean_value(extracted_data.get('ubicacion_agente') or extracted_data.get('DIRECCION_AEROLINEA'))
                
                # El itinerario de Sabre se encuentra en la clave 'vuelos'
                if 'vuelos' in extracted_data:
                    self.ruta_vuelo = json.dumps(extracted_data['vuelos'], indent=2, ensure_ascii=False)
                else:
                    self.ruta_vuelo = extracted_data.get('ITINERARIO_DE_VUELO') or extracted_data.get('ItinerarioFinalLimpio', '')

                self.impuestos_descripcion = ticket_parser._clean_value(extracted_data.get('IMPUESTOS'))
                self.tarifa_base = ticket_parser.string_a_decimal(extracted_data.get('TARIFA'))
                self.total_boleto = ticket_parser.string_a_decimal(extracted_data.get('TOTAL'))
                if self.impuestos_descripcion and self.impuestos_descripcion != 'No encontrado':
                    tax_values = re.findall(r'([\d,]+\.\d{2})', self.impuestos_descripcion)
                    self.impuestos_total_calculado = sum(ticket_parser.string_a_decimal(tv) for tv in tax_values)
                
                log_parseo_list.append(str(_("Parseo de archivo completado.")))
                logger.debug("Boleto ID %s - Parseo de archivo completado", self.id_boleto_importado)

            else: # Entrada Manual
                log_parseo_list.append(str(_("Procesando entrada manual.")))
                if not self.datos_parseados:
                    raise ValueError("Entrada manual no contiene datos_parseados para procesar.")
                log_parseo_list.append(str(_("Datos de entrada manual validados.")))
                logger.debug("Boleto ID %s - Procesamiento manual listo (entrada manual)", self.id_boleto_importado)

            self.estado_parseo = BoletoImportado.EstadoParseo.COMPLETADO

            # --- Lógica de Asociación y Creación ---
            cliente_encontrado = None
            if self.foid_pasajero and self.foid_pasajero != 'No encontrado':
                cliente_encontrado = Cliente.objects.filter(numero_pasaporte=self.foid_pasajero).first()
            
            if not cliente_encontrado and self.nombre_pasajero_procesado:
                # Lógica para encontrar cliente por nombre
                pass

            pasajero_obj, created = Pasajero.objects.get_or_create(
                numero_documento=self.foid_pasajero,
                defaults={
                    'nombres': self.nombre_pasajero_procesado.split(' ')[0],
                    'apellidos': ' '.join(self.nombre_pasajero_procesado.split(' ')[1:]),
                }
            )
            if created:
                log_parseo_list.append(f"Pasajero '{pasajero_obj}' creado.")
            else:
                log_parseo_list.append(f"Pasajero '{pasajero_obj}' encontrado.")

            if cliente_encontrado:
                try:
                    moneda_boleto_codigo = re.search(r'([A-Z]{3})', self.datos_parseados.get('TARIFA', '')).group(1) if re.search(r'([A-Z]{3})', self.datos_parseados.get('TARIFA', '')) else 'USD'
                    moneda_venta = Moneda.objects.filter(codigo_iso=moneda_boleto_codigo).first() or Moneda.objects.filter(es_moneda_local=True).first()
                    
                    venta_auto, venta_created = Venta.objects.get_or_create(
                        localizador=self.localizador_pnr,
                        defaults={
                            'cliente': cliente_encontrado,
                            'moneda': moneda_venta,
                            'subtotal': self.tarifa_base or Decimal('0.00'),
                            'impuestos': self.impuestos_total_calculado or Decimal('0.00'),
                            'descripcion_general': f"Venta automática de boleto {self.numero_boleto}",
                            'estado': Venta.EstadoVenta.PENDIENTE_PAGO,
                        }
                    )
                    venta_auto.pasajeros.add(pasajero_obj)
                    self.venta_asociada = venta_auto
                    log_parseo_list.append(f"Venta {'creada' if venta_created else 'encontrada'}: {venta_auto.localizador}")

                except Exception as e_venta:
                    log_parseo_list.append(f"Error al crear/asociar venta: {e_venta}")
            else:
                log_parseo_list.append("No se encontró cliente para asociar la venta.")

            if self.datos_parseados:
                try:
                    # Para SABRE usar el nuevo generador con transformación avanzada; para KIU mantener compatibilidad.
                    source_system = self.datos_parseados.get('SOURCE_SYSTEM')
                    if source_system == 'SABRE':
                        # Normalizar a clave esperada por pdf_generator
                        data_for_pdf = dict(self.datos_parseados)
                        data_for_pdf['SOURCE_SYSTEM'] = 'SABRE'  # asegurar valor aceptado
                        pdf_bytes, pdf_filename = pdf_generator.generate_ticket_pdf(data_for_pdf)
                    else:
                        # Ruta legacy KIU (plantilla antigua)
                        pdf_bytes, pdf_filename = ticket_parser.generate_ticket(self.datos_parseados)
                    self.archivo_pdf_generado.save(pdf_filename, ContentFile(pdf_bytes), save=False)
                    log_parseo_list.append(f"PDF unificado '{pdf_filename}' generado.")
                except Exception as e_pdf:
                    log_parseo_list.append(f"Error generando PDF: {e_pdf}")

        except Exception as e:
            log_parseo_list.append(f"Error GRAVE: {e}")
            self.estado_parseo = BoletoImportado.EstadoParseo.ERROR_PARSEO
            if self.datos_parseados is None:
                self.datos_parseados = {}
            self.datos_parseados['error'] = str(e)

        finally:
            self.log_parseo = "\n".join(log_parseo_list)
            self.save()

# --- CMS Models ---
class PaginaCMS(models.Model):
    id_pagina_cms = models.AutoField(primary_key=True, verbose_name=_("ID Página CMS"))
    titulo = models.CharField(_("Título de la Página"), max_length=200, validators=[validar_no_vacio_o_espacios])
    slug = models.SlugField(_("Slug (URL amigable)"), max_length=255, unique=True, help_text=_("Se genera automáticamente si se deja vacío, o se puede especificar."))
    contenido = models.TextField(_("Contenido HTML/Markdown"), blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)
    class EstadoPublicacion(models.TextChoices): PUBLICADO = 'PUB', _('Publicado'); BORRADOR = 'BOR', _('Borrador'); ARCHIVADO = 'ARC', _('Archivado')
    estado = models.CharField(_("Estado de Publicación"), max_length=3, choices=EstadoPublicacion.choices, default=EstadoPublicacion.BORRADOR)
    plantilla = models.CharField(_("Plantilla Django a usar"), max_length=100, blank=True, null=True, help_text=_("Ej: 'cms/pagina_detalle.html'. Si está vacío, usa una por defecto."))
    meta_titulo = models.CharField(_("Meta Título (SEO)"), max_length=255, blank=True)
    meta_descripcion = models.TextField(_("Meta Descripción (SEO)"), blank=True)
    class Meta:
        verbose_name = _("Página CMS")
        verbose_name_plural = _("Páginas CMS")
        ordering = ['titulo']
    def __str__(self): return self.titulo
    def save(self, *args, **kwargs):
        if not self.slug: from django.utils.text import slugify; self.slug = slugify(self.titulo); original_slug = self.slug; counter = 1
        while PaginaCMS.objects.filter(slug=self.slug).exclude(pk=self.pk).exists(): self.slug = f"{original_slug}-{counter}"; counter += 1
        super().save(*args, **kwargs)

class DestinoCMS(models.Model):
    id_destino_cms = models.AutoField(primary_key=True, verbose_name=_("ID Destino CMS"))
    nombre = models.CharField(_("Nombre del Destino"), max_length=150, unique=True, validators=[validar_no_vacio_o_espacios])
    slug = models.SlugField(_("Slug"), max_length=170, unique=True)
    pais_ubicacion = models.ForeignKey(Pais, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("País de Ubicación"))
    descripcion_corta = models.TextField(_("Descripción Corta"), blank=True)
    descripcion_larga = models.TextField(_("Descripción Larga/Detallada"), blank=True)
    imagen_destacada = models.ImageField(_("Imagen Destacada"), upload_to='cms/destinos/', blank=True, null=True)
    mejor_epoca_viajar = models.CharField(_("Mejor Época para Viajar"), max_length=255, blank=True)
    atracciones_principales = models.TextField(_("Atracciones Principales (lista)"), blank=True, help_text=_("Separar por comas o un punto por línea."))
    estado = models.CharField(_("Estado"), max_length=3, choices=PaginaCMS.EstadoPublicacion.choices, default=PaginaCMS.EstadoPublicacion.BORRADOR)
    meta_titulo = models.CharField(_("Meta Título (SEO)"), max_length=255, blank=True)
    meta_descripcion = models.TextField(_("Meta Descripción (SEO)"), blank=True)
    class Meta:
        verbose_name = _("Destino CMS")
        verbose_name_plural = _("Destinos CMS")
        ordering = ['nombre']
    def __str__(self): return self.nombre
    def save(self, *args, **kwargs):
        if not self.slug: from django.utils.text import slugify; self.slug = slugify(self.nombre)
        super().save(*args, **kwargs)

class PaqueteTuristicoCMS(models.Model):
    id_paquete_cms = models.AutoField(primary_key=True, verbose_name=_("ID Paquete CMS"))
    titulo = models.CharField(_("Título del Paquete"), max_length=255, validators=[validar_no_vacio_o_espacios])
    slug = models.SlugField(_("Slug"), max_length=255, unique=True)
    destino_principal = models.ForeignKey(DestinoCMS, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("Destino Principal"))
    descripcion_corta = models.TextField(_("Descripción Corta"), blank=True)
    itinerario_detallado = models.TextField(_("Itinerario Detallado"), blank=True)
    duracion_dias = models.PositiveSmallIntegerField(_("Duración (días)"), null=True, blank=True)
    precio_desde_texto = models.CharField(_("Precio Desde (texto)"), max_length=100, blank=True, help_text=_("Ej: $1,200 p/p base doble"))
    precio_numerico = models.DecimalField(_("Precio Numérico (para filtros)"), max_digits=10, decimal_places=2, null=True, blank=True)
    moneda_paquete = models.ForeignKey(Moneda, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("Moneda del Paquete"))
    incluye = models.TextField(_("Qué Incluye el Paquete"), blank=True)
    no_incluye = models.TextField(_("Qué NO Incluye el Paquete"), blank=True)
    imagen_destacada = models.ImageField(_("Imagen Destacada"), upload_to='cms/paquetes/', blank=True, null=True)
    fecha_validez_inicio = models.DateField(_("Válido Desde"), null=True, blank=True)
    fecha_validez_fin = models.DateField(_("Válido Hasta"), null=True, blank=True)
    class EstadoPaquete(models.TextChoices): ACTIVO = 'ACT', _('Activo'); INACTIVO = 'INA', _('Inactivo'); AGOTADO = 'AGO', _('Agotado'); BORRADOR = 'BOR', _('Borrador')
    estado = models.CharField(_("Estado del Paquete"), max_length=3, choices=EstadoPaquete.choices, default=EstadoPaquete.BORRADOR)
    es_destacado = models.BooleanField(_("Paquete Destacado"), default=False, help_text=_("Mostrar en la página principal o secciones destacadas."))
    meta_titulo = models.CharField(_("Meta Título (SEO)"), max_length=255, blank=True)
    meta_descripcion = models.TextField(_("Meta Descripción (SEO)"), blank=True)
    class Meta:
        verbose_name = _("Paquete Turístico CMS")
        verbose_name_plural = _("Paquetes Turísticos CMS")
        ordering = ['-es_destacado', 'titulo']
    def __str__(self): return f"{self.titulo}"
    def save(self, *args, **kwargs):
        if not self.slug: from django.utils.text import slugify; self.slug = slugify(self.titulo)
        super().save(*args, **kwargs)

class ArticuloBlog(models.Model):
    id_articulo = models.AutoField(primary_key=True, verbose_name=_("ID Artículo"))
    titulo = models.CharField(_("Título del Artículo"), max_length=255, validators=[validar_no_vacio_o_espacios])
    slug = models.SlugField(_("Slug"), max_length=255, unique=True)
    contenido = models.TextField(_("Contenido del Artículo"))
    extracto = models.TextField(_("Extracto o Resumen"), blank=True)
    fecha_publicacion = models.DateTimeField(_("Fecha de Publicación"), null=True, blank=True, help_text=_("Si está en blanco y el estado es 'Publicado', se usará la fecha actual."))
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)
    imagen_destacada = models.ImageField(_("Imagen Destacada"), upload_to='cms/blog/', blank=True, null=True)
    estado = models.CharField(_("Estado"), max_length=3, choices=PaginaCMS.EstadoPublicacion.choices, default=PaginaCMS.EstadoPublicacion.BORRADOR)
    permitir_comentarios = models.BooleanField(_("Permitir Comentarios"), default=True)
    meta_titulo = models.CharField(_("Meta Título (SEO)"), max_length=255, blank=True)
    meta_descripcion = models.TextField(_("Meta Descripción (SEO)"), blank=True)
    class Meta:
        verbose_name = _("Artículo de Blog")
        verbose_name_plural = _("Artículos de Blog")
        ordering = ['-fecha_publicacion', '-fecha_creacion']
    def __str__(self): return self.titulo
    def save(self, *args, **kwargs):
        if not self.slug: from django.utils.text import slugify; self.slug = slugify(self.titulo)
        if self.estado == PaginaCMS.EstadoPublicacion.PUBLICADO and not self.fecha_publicacion: self.fecha_publicacion = timezone.now()
        super().save(*args, **kwargs)

class Testimonio(models.Model):
    id_testimonio = models.AutoField(primary_key=True, verbose_name=_("ID Testimonio"))
    nombre_cliente = models.CharField(_("Nombre del Cliente"), max_length=150, validators=[validar_no_vacio_o_espacios])
    texto_testimonio = models.TextField(_("Texto del Testimonio"), validators=[validar_no_vacio_o_espacios])
    calificacion = models.PositiveSmallIntegerField(_("Calificación (1-5)"), null=True, blank=True, choices=[(i, str(i)) for i in range(1, 6)])
    fecha_recibido = models.DateField(_("Fecha Recibido/Viaje"), default=timezone.now)
    class EstadoTestimonio(models.TextChoices): PENDIENTE = 'PEN', _('Pendiente de Aprobación'); APROBADO = 'APR', _('Aprobado y Visible'); RECHAZADO = 'REC', _('Rechazado')
    estado = models.CharField(_("Estado"), max_length=3, choices=EstadoTestimonio.choices, default=EstadoTestimonio.PENDIENTE)
    origen = models.CharField(_("Origen del Testimonio"), max_length=50, blank=True, help_text=_("Ej: Formulario web, Email, Red social"))
    class Meta:
        verbose_name = _("Testimonio")
        verbose_name_plural = _("Testimonios")
        ordering = ['-fecha_recibido']
    def __str__(self): return f"Testimonio de {self.nombre_cliente} ({self.get_estado_display()})"

class MenuItemCMS(models.Model):
    titulo = models.CharField(_("Título del Enlace"), max_length=100)
    url_enlace = models.CharField(_("URL (si es externa o manual)"), max_length=255, blank=True, help_text=_("Dejar vacío si se enlaza a contenido interno."))
    pagina_enlazada = models.ForeignKey(PaginaCMS, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("Página CMS Enlazada"))
    destino_enlazado = models.ForeignKey(DestinoCMS, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("Destino CMS Enlazado"))
    paquete_enlazado = models.ForeignKey(PaqueteTuristicoCMS, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("Paquete CMS Enlazado"))
    menu_padre = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='sub_items', verbose_name=_("Item Padre (para submenús)"))
    orden = models.PositiveIntegerField(_("Orden de Aparición"), default=0)
    abrir_en_nueva_pestana = models.BooleanField(_("Abrir en Nueva Pestaña"), default=False)

    class UbicacionMenu(models.TextChoices):
        PRINCIPAL = 'NAV_PRINCIPAL', _('Navegación Principal')
        FOOTER_1 = 'FOOTER_1', _('Pie de Página (Columna 1)')
        FOOTER_2 = 'FOOTER_2', _('Pie de Página (Columna 2)')
        OTRO = 'OTRO', _('Otra Ubicación')

    ubicacion = models.CharField(
        _("Ubicación del Menú"),
        max_length=20,
        choices=UbicacionMenu.choices,
        default=UbicacionMenu.PRINCIPAL,
        db_index=True
    )

    class Meta:
        verbose_name = _("Item de Menú CMS")
        verbose_name_plural = _("Items de Menú CMS")
        ordering = ['ubicacion', 'orden', 'titulo']

    def __str__(self):
        return f"{self.titulo} ({self.get_ubicacion_display()})"

    def get_url(self):
        if self.url_enlace:
            return self.url_enlace
        
        if self.pagina_enlazada:
            try:
                return reverse('core:pagina_cms_detalle', kwargs={'slug': self.pagina_enlazada.slug})
            except NoReverseMatch: 
                return f"/paginas/{self.pagina_enlazada.slug}/" 
        
        if self.destino_enlazado:
            try: 
                return reverse('core:destino_cms_detalle', kwargs={'slug': self.destino_enlazado.slug})
            except NoReverseMatch:
                 return f"/destinos/{self.destino_enlazado.slug}/" 
        
        if self.paquete_enlazado:
            try: 
                return reverse('core:paquete_cms_detalle', kwargs={'slug': self.paquete_enlazado.slug})
            except NoReverseMatch:
                return f"/paquetes/{self.paquete_enlazado.slug}/"
        return "#"

    def clean(self):
        enlaces_internos = [
            self.pagina_enlazada,
            self.destino_enlazado,
            self.paquete_enlazado,
        ]
        enlaces_definidos = sum(1 for enlace in enlaces_internos if enlace is not None)

        if self.url_enlace and enlaces_definidos > 0:
            raise ValidationError(_("No puede especificar una URL manual y un enlace a contenido interno al mismo tiempo."))
        if not self.url_enlace and enlaces_definidos == 0:
            pass 
        if enlaces_definidos > 1:
            raise ValidationError(_("Solo puede enlazar a un tipo de contenido interno a la vez."))


class FormularioContactoCMS(models.Model):
    id_envio = models.AutoField(primary_key=True, verbose_name=_("ID Envío"))
    nombre_completo = models.CharField(_("Nombre Completo"), max_length=150)
    email = models.EmailField(_("Correo Electrónico"))
    telefono = models.CharField(_("Teléfono"), max_length=30, blank=True)
    asunto = models.CharField(_("Asunto"), max_length=200, blank=True)
    mensaje = models.TextField(_("Mensaje"))
    fecha_envio = models.DateTimeField(_("Fecha de Envío"), auto_now_add=True)
    ip_origen = models.GenericIPAddressField(_("Dirección IP de Origen"), null=True, blank=True)
    class EstadoLectura(models.TextChoices): NO_LEIDO = 'NOL', _('No Leído'); LEIDO = 'LEI', _('Leído'); PROCESADO = 'PRO', _('Procesado/Respondido'); SPAM = 'SPM', _('Spam')
    estado_lectura = models.CharField(_("Estado de Lectura"), max_length=3, choices=EstadoLectura.choices, default=EstadoLectura.NO_LEIDO)
    class Meta:
        verbose_name = _("Envío de Formulario de Contacto")
        verbose_name_plural = _("Envíos de Formularios de Contacto")
        ordering = ['-fecha_envio']
    def __str__(self): return f"Envío de {self.nombre_completo} ({self.email}) el {self.fecha_envio.strftime('%Y-%m-%d %H:%M')}"

# Señales (Signals)
@receiver(post_save, sender=BoletoImportado)
def trigger_boleto_parse(sender, instance, created, **kwargs):
    logger.debug("Signal trigger_boleto_parse para boleto ID %s created=%s estado=%s", instance.id_boleto_importado, created, instance.estado_parseo)
    if created or (instance.estado_parseo == BoletoImportado.EstadoParseo.PENDIENTE):
        if instance.estado_parseo not in (BoletoImportado.EstadoParseo.EN_PROCESO, BoletoImportado.EstadoParseo.COMPLETADO):
            logger.debug("Invocando parsear_boleto() para boleto ID %s", instance.id_boleto_importado)
            instance.parsear_boleto()
        else:
            logger.debug("parsear_boleto() omitido para boleto ID %s por estado actual", instance.id_boleto_importado)
    else:
        logger.debug("parsear_boleto() omitido para boleto ID %s por condición de creación/estado", instance.id_boleto_importado)

@receiver(post_save, sender=ItemCotizacion)
def actualizar_totales_cotizacion_desde_item(sender, instance, **kwargs):
    if instance.cotizacion:
        instance.cotizacion.calcular_totales_desde_items()

@receiver(post_save, sender=DetalleAsiento)
def actualizar_totales_asiento_desde_detalle(sender, instance, **kwargs):
    if instance.asiento:
        instance.asiento.calcular_totales()

# --- Signals de recálculo financiero de Venta ---
@receiver(post_save, sender=FeeVenta)
def recalc_venta_por_fee(sender, instance, created, **kwargs):
    # Siempre recalculamos pues puede cambiar monto (updates). Evitar bucles infinitos: recalcular_finanzas no guarda Fee.
    instance.venta.recalcular_finanzas()

@receiver(post_save, sender=PagoVenta)
def recalc_venta_por_pago(sender, instance, created, **kwargs):
    if instance.confirmado:
        instance.venta.recalcular_finanzas()
        # Asegurar evaluación de puntos incluso si no cambió estado
        instance.venta._evaluar_otorgar_puntos(contexto="signal_pago_post_save")
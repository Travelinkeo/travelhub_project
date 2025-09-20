"""Modelos de Personas (Cliente, Pasajero).

Estos modelos se separan en su propia app `personas` para romper dependencias
circulares y permitir una carga controlada.
"""
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError

from core.models_catalogos import Pais, Ciudad

def validar_no_vacio_o_espacios(value):
    if not value or (isinstance(value, str) and not value.strip()):
        raise ValidationError(_("Este campo no puede estar vacío o contener solo espacios en blanco."))

def validar_numero_pasaporte(value):
    if not value: return
    import re
    if not re.match(r'^[A-Z0-9<]{1,20}$', value):
        raise ValidationError(_("Número de pasaporte inválido. Use solo mayúsculas, números y el carácter '<'."))

class Cliente(models.Model):
    id_cliente = models.AutoField(primary_key=True, verbose_name=_("ID Cliente"))
    class TipoCliente(models.TextChoices):
        PARTICULAR = 'PAR', _('Particular')
        EMPRESA = 'EMP', _('Empresa')
    tipo_cliente = models.CharField(_("Tipo de Cliente"), max_length=3, choices=TipoCliente.choices, default=TipoCliente.PARTICULAR)
    nombres = models.CharField(_("Nombres"), max_length=150, blank=True, null=True)
    apellidos = models.CharField(_("Apellidos"), max_length=150, blank=True, null=True)
    nombre_empresa = models.CharField(_("Nombre de la Empresa"), max_length=200, blank=True, null=True)
    email = models.EmailField(_("Correo Electrónico"), unique=True, blank=True, null=True)
    telefono_principal = models.CharField(_("Teléfono Principal"), max_length=30, blank=True, null=True)
    fecha_nacimiento = models.DateField(_("Fecha de Nacimiento"), blank=True, null=True)
    nacionalidad = models.ForeignKey(Pais, related_name='clientes_nacionales', on_delete=models.SET_NULL, blank=True, null=True, verbose_name=_("Nacionalidad"))
    numero_pasaporte = models.CharField(_("Número de Pasaporte"), max_length=20, blank=True, null=True, validators=[validar_numero_pasaporte])
    pais_emision_pasaporte = models.ForeignKey(Pais, related_name='pasaportes_emitidos', on_delete=models.SET_NULL, blank=True, null=True, verbose_name=_("País de Emisión del Pasaporte"))
    fecha_expiracion_pasaporte = models.DateField(_("Fecha de Expiración del Pasaporte"), blank=True, null=True)
    direccion = models.TextField(_("Dirección"), blank=True, null=True)
    ciudad = models.ForeignKey(Ciudad, on_delete=models.SET_NULL, blank=True, null=True, verbose_name=_("Ciudad"), related_name='personas_clientes')
    puntos_fidelidad = models.PositiveIntegerField(_("Puntos de Fidelidad"), default=0)
    es_cliente_frecuente = models.BooleanField(_("Es Cliente Frecuente"), default=False)
    class Meta:
        verbose_name = _("Cliente")
        verbose_name_plural = _("Clientes")
        ordering = ['apellidos', 'nombres', 'nombre_empresa']
    def __str__(self):
        if self.tipo_cliente == self.TipoCliente.EMPRESA:
            return self.nombre_empresa or f"Cliente Empresa #{self.id_cliente}"
        return f"{self.nombres or ''} {self.apellidos or ''}".strip() or f"Cliente Particular #{self.id_cliente}"
    def get_nombre_completo(self):
        return f"{self.nombres} {self.apellidos}" if self.tipo_cliente == self.TipoCliente.PARTICULAR else self.nombre_empresa
    get_nombre_completo.short_description = _("Nombre Completo / Empresa")
    def clean(self):
        if self.tipo_cliente == self.TipoCliente.PARTICULAR and (not self.nombres or not self.apellidos):
            raise ValidationError(_("Para clientes particulares, nombres y apellidos son obligatorios."))
        if self.tipo_cliente == self.TipoCliente.EMPRESA and not self.nombre_empresa:
            raise ValidationError(_("Para clientes empresa, el nombre de la empresa es obligatorio."))
    def calcular_cliente_frecuente(self):
        self.es_cliente_frecuente = self.puntos_fidelidad >= 1000

class Pasajero(models.Model):
    id_pasajero = models.AutoField(primary_key=True, verbose_name=_("ID Pasajero"))
    nombres = models.CharField(_("Nombres"), max_length=150, validators=[validar_no_vacio_o_espacios])
    apellidos = models.CharField(_("Apellidos"), max_length=150, validators=[validar_no_vacio_o_espacios])
    fecha_nacimiento = models.DateField(_("Fecha de Nacimiento"), blank=True, null=True)
    class TipoDocumento(models.TextChoices):
        PASAPORTE = 'PASS', _('Pasaporte')
        CEDULA = 'CI', _('Cédula/DNI')
        OTRO = 'OTR', _('Otro')
    tipo_documento = models.CharField(_("Tipo de Documento"), max_length=4, choices=TipoDocumento.choices, default=TipoDocumento.PASAPORTE)
    numero_documento = models.CharField(_("Número de Documento"), max_length=50, unique=True)
    nacionalidad = models.ForeignKey(Pais, related_name='pasajeros_nacionales', on_delete=models.SET_NULL, blank=True, null=True, verbose_name=_("Nacionalidad"))
    pais_emision = models.ForeignKey(Pais, related_name='documentos_emitidos', on_delete=models.SET_NULL, blank=True, null=True, verbose_name=_("País de Emisión"))
    fecha_expiracion_documento = models.DateField(_("Fecha de Expiración"), blank=True, null=True)
    email = models.EmailField(_("Correo Electrónico"), blank=True, null=True)
    telefono = models.CharField(_("Teléfono"), max_length=30, blank=True, null=True)
    class Meta:
        verbose_name = _("Pasajero")
        verbose_name_plural = _("Pasajeros")
        ordering = ['apellidos', 'nombres']
    def __str__(self):
        return f"{self.nombres} {self.apellidos}"

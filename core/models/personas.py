from __future__ import annotations

import logging

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from core.models_catalogos import Ciudad, Pais
from core.validators import validar_no_vacio_o_espacios, validar_numero_pasaporte

logger = logging.getLogger(__name__)

class Pasajero(models.Model):
    id_pasajero = models.AutoField(primary_key=True, verbose_name=_('ID Pasajero'))
    nombres = models.CharField(_('Nombres'), max_length=100, validators=[validar_no_vacio_o_espacios])
    apellidos = models.CharField(_('Apellidos'), max_length=100, validators=[validar_no_vacio_o_espacios])
    fecha_nacimiento = models.DateField(_('Fecha de Nacimiento'), blank=True, null=True)
    class TipoDocumentoChoices(models.TextChoices):
        PASAPORTE = 'PASS', _('Pasaporte')
        CEDULA = 'CI', _('Cédula de Identidad')
        OTRO = 'OTRO', _('Otro')
    tipo_documento = models.CharField(_('Tipo de Documento'), max_length=4, choices=TipoDocumentoChoices.choices, default=TipoDocumentoChoices.PASAPORTE)
    numero_documento = models.CharField(_('Número de Documento/Pasaporte'), max_length=50, unique=True, validators=[validar_numero_pasaporte])
    pais_emision_documento = models.ForeignKey(Pais, on_delete=models.SET_NULL, blank=True, null=True, verbose_name=_('País Emisión Documento'))
    fecha_vencimiento_documento = models.DateField(_('Fecha Vencimiento Documento'), blank=True, null=True)
    nacionalidad = models.ForeignKey(Pais, related_name='pasajeros_nacionalidad', on_delete=models.SET_NULL, blank=True, null=True, verbose_name=_('Nacionalidad'))
    email = models.EmailField(_('Correo Electrónico'), max_length=255, blank=True, null=True)
    telefono = models.CharField(_('Teléfono'), max_length=30, blank=True, null=True)
    notas = models.TextField(_('Notas sobre el Pasajero'), blank=True, null=True)
    class Meta:
        verbose_name = _('Pasajero')
        verbose_name_plural = _('Pasajeros')
        ordering = ['apellidos', 'nombres']
        unique_together = ('nombres', 'apellidos', 'fecha_nacimiento')
    def __str__(self):  # pragma: no cover
        return f"{self.nombres} {self.apellidos}"
    def get_nombre_completo(self):  # pragma: no cover
        return f"{self.nombres} {self.apellidos}".strip()


class Cliente(models.Model):
    id_cliente = models.AutoField(primary_key=True, verbose_name=_('ID Cliente'))
    nombres = models.CharField(_('Nombres'), max_length=100, validators=[validar_no_vacio_o_espacios])
    apellidos = models.CharField(_('Apellidos'), max_length=100, blank=True, null=True)
    nombre_empresa = models.CharField(_('Nombre de Empresa'), max_length=150, blank=True, null=True)
    email = models.EmailField(_('Correo Electrónico'), max_length=255, unique=True, blank=True, null=True)
    telefono_principal = models.CharField(_('Teléfono Principal'), max_length=30, blank=True, null=True)
    telefono_secundario = models.CharField(_('Teléfono Secundario'), max_length=30, blank=True, null=True)
    direccion_linea1 = models.CharField(_('Dirección Línea 1'), max_length=255, blank=True, null=True)
    direccion_linea2 = models.CharField(_('Dirección Línea 2'), max_length=255, blank=True, null=True)
    ciudad = models.ForeignKey(Ciudad, on_delete=models.SET_NULL, blank=True, null=True, verbose_name=_('Ciudad'), related_name='core_clientes')
    codigo_postal = models.CharField(_('Código Postal'), max_length=20, blank=True, null=True)
    fecha_nacimiento = models.DateField(_('Fecha de Nacimiento'), blank=True, null=True)
    numero_pasaporte = models.CharField(_('Número de Pasaporte'), max_length=50, blank=True, null=True, validators=[validar_numero_pasaporte])
    pais_emision_pasaporte = models.ForeignKey(Pais, related_name='clientes_pasaporte_emitido', on_delete=models.SET_NULL, blank=True, null=True, verbose_name=_('País Emisión Pasaporte'))
    fecha_vencimiento_pasaporte = models.DateField(_('Fecha Vencimiento Pasaporte'), blank=True, null=True)
    nacionalidad = models.ForeignKey(Pais, related_name='clientes_nacionalidad', on_delete=models.SET_NULL, blank=True, null=True, verbose_name=_('Nacionalidad'))
    preferencias_viaje = models.TextField(_('Preferencias de Viaje'), blank=True, null=True)
    notas_cliente = models.TextField(_('Notas sobre el Cliente'), blank=True, null=True)
    fecha_registro = models.DateTimeField(_('Fecha de Registro'), default=timezone.now)
    class TipoCliente(models.TextChoices):
        INDIVIDUAL = 'IND', _('Individual')
        CORPORATIVO = 'COR', _('Corporativo')
        VIP = 'VIP', _('VIP')
        OTRO = 'OTR', _('Otro')
    tipo_cliente = models.CharField(_('Tipo de Cliente'), max_length=3, choices=TipoCliente.choices, default=TipoCliente.INDIVIDUAL)
    puntos_fidelidad = models.PositiveIntegerField(_('Puntos de Fidelidad'), default=0, help_text=_('Puntos acumulados por el cliente.'))
    es_cliente_frecuente = models.BooleanField(_('Es Cliente Frecuente'), default=False, editable=False)
    class Meta:
        verbose_name = _('Cliente')
        verbose_name_plural = _('Clientes')
        ordering = ['apellidos', 'nombres', 'nombre_empresa']
    def __str__(self):  # pragma: no cover
        return self.nombre_empresa if self.nombre_empresa else f"{self.nombres} {self.apellidos or ''}".strip()
    def get_nombre_completo(self):  # pragma: no cover
        return f"{self.nombres} {self.apellidos or ''}".strip()
    get_nombre_completo.short_description = _('Nombre Completo')
    def calcular_cliente_frecuente(self, umbral_puntos=1000, umbral_compras=5):  # pragma: no cover
        self.es_cliente_frecuente = self.puntos_fidelidad >= umbral_puntos
        return self.es_cliente_frecuente
    def clean(self):  # pragma: no cover
        if not self.nombre_empresa and (not self.nombres or not self.apellidos):
            raise ValidationError(_('Si no es una empresa, debe proporcionar nombres y apellidos.'))
        if self.email and Cliente.objects.filter(email=self.email).exclude(pk=self.pk).exists():
            raise ValidationError({'email': _('Ya existe un cliente con este correo electrónico.')})

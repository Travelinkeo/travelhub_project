from __future__ import annotations

import logging

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.html import strip_tags
from django.utils.translation import gettext_lazy as _

# Imports cruzados (mantener referencia a core por ahora)
from core.models_catalogos import Ciudad, Pais
from core.validators import validar_no_vacio_o_espacios, validar_numero_pasaporte
from core.fields import EncryptedCharField

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
    numero_documento = EncryptedCharField(_('Número de Documento/Pasaporte'), max_length=50, unique=True, validators=[validar_numero_pasaporte])
    agencia = models.ForeignKey('core.Agencia', on_delete=models.CASCADE, null=True, blank=True, verbose_name=_('Agencia'))
    
    # --- CAMPOS RESTAURADOS Y SINCRONIZADOS ---
    pais_emision_documento = models.ForeignKey(
        Pais, 
        on_delete=models.SET_NULL, 
        blank=True, 
        null=True, 
        verbose_name=_('País Emisión Documento'),
        db_column='pais_emision_id'  # Sincronizado con DB física
    )
    fecha_emision_documento = models.DateField(
        _('Fecha Emisión Documento'), 
        blank=True, 
        null=True, 
        help_text=_('Fecha de emisión del pasaporte/documento')
    )
    fecha_vencimiento_documento = models.DateField(
        _('Fecha Vencimiento Documento'), 
        blank=True, 
        null=True,
        db_column='fecha_expiracion_documento'  # Sincronizado con DB física
    )
    nacionalidad = models.ForeignKey(
        Pais, 
        related_name='crm_pasajeros_nacionalidad', 
        on_delete=models.SET_NULL, 
        blank=True, 
        null=True, 
        verbose_name=_('Nacionalidad')
    )
    
    tiene_fiebre_amarilla = models.BooleanField(
        _('Tiene Vacuna Fiebre Amarilla'), 
        default=False, 
        help_text=_('¿El pasajero tiene la vacuna de fiebre amarilla?')
    )
    fecha_vacuna_fiebre_amarilla = models.DateField(
        _('Fecha Vacuna Fiebre Amarilla'), 
        blank=True, 
        null=True, 
        help_text=_('Fecha de aplicación de la vacuna (válida por 10 años)')
    )
    email = models.EmailField(_('Correo Electrónico'), max_length=255, blank=True, null=True)
    telefono = models.CharField(_('Teléfono'), max_length=30, blank=True, null=True)
    preferencias = models.JSONField(_('Preferencias'), default=dict, blank=True)
    notas = models.TextField(_('Notas sobre el Pasajero'), blank=True, null=True)

    class Meta:
        verbose_name = _('Pasajero')
        verbose_name_plural = _('Pasajeros')
        ordering = ['apellidos', 'nombres']
        db_table = 'personas_pasajero'
        managed = True

    def __str__(self):
        return strip_tags(f"{self.nombres} {self.apellidos}")
    def get_nombre_completo(self):
        return strip_tags(f"{self.nombres} {self.apellidos}").strip()


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
    direccion = models.TextField(_('Dirección'), blank=True, null=True) # Legacy field
    ciudad = models.ForeignKey(Ciudad, on_delete=models.SET_NULL, blank=True, null=True, verbose_name=_('Ciudad'), related_name='crm_clientes')
    codigo_postal = models.CharField(_('Código Postal'), max_length=20, blank=True, null=True)
    fecha_nacimiento = models.DateField(_('Fecha de Nacimiento'), blank=True, null=True)
    
    # Campo cifrado para seguridad de datos sensibles
    numero_pasaporte = EncryptedCharField(
        _('Número de Pasaporte'), 
        max_length=50, 
        blank=True, 
        null=True, 
        validators=[validar_numero_pasaporte]
    )
    
    cedula_identidad = models.CharField(_('Cédula de Identidad'), max_length=20, blank=True, null=True)
    pais_emision_pasaporte = models.ForeignKey(Pais, related_name='crm_clientes_pasaporte_emitido', on_delete=models.SET_NULL, blank=True, null=True, verbose_name=_('País Emisión Pasaporte'))
    fecha_expiracion_pasaporte = models.DateField(_('Fecha Expiración Pasaporte'), blank=True, null=True)
    nacionalidad = models.ForeignKey(Pais, related_name='crm_clientes_nacionalidad', on_delete=models.SET_NULL, blank=True, null=True, verbose_name=_('Nacionalidad'))
    
    preferencias_viaje = models.TextField(_('Preferencias de Viaje'), blank=True, null=True)
    notas_cliente = models.TextField(_('Notas sobre el Cliente'), blank=True, null=True)
    fecha_registro = models.DateTimeField(_('Fecha de Registro'), default=timezone.now)
    
    # Adicionales de la DB física
    agencia = models.ForeignKey('core.Agencia', on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_('Agencia'))
    foto_perfil = models.ImageField(_('Foto de Perfil'), upload_to='clientes/fotos/', blank=True, null=True)

    class TipoCliente(models.TextChoices):
        INDIVIDUAL = 'IND', _('Individual')
        CORPORATIVO = 'COR', _('Corporativo')
        VIP = 'VIP', _('VIP')
        OTRO = 'OTR', _('Otro')
    tipo_cliente = models.CharField(_('Tipo de Cliente'), max_length=3, choices=TipoCliente.choices, default=TipoCliente.INDIVIDUAL)
    puntos_fidelidad = models.PositiveIntegerField(_('Puntos de Fidelidad'), default=0, help_text=_('Puntos acumulados por el cliente.'))
    es_cliente_frecuente = models.BooleanField(_('Es Cliente Frecuente'), default=False, editable=False)
    pasajeros = models.ManyToManyField(Pasajero, related_name='clientes', blank=True, verbose_name=_('Pasajeros Vinculados'))
    
    class Meta:
        verbose_name = _('Cliente')
        verbose_name_plural = _('Clientes')
        ordering = ['apellidos', 'nombres', 'nombre_empresa']
        db_table = 'personas_cliente'
        managed = True
        indexes = [
            models.Index(fields=['agencia', 'apellidos']),
            models.Index(fields=['agencia', 'cedula_identidad']),
            models.Index(fields=['agencia', 'email']),
        ]
    
    def __str__(self):
        name = self.nombre_empresa if self.nombre_empresa else f"{self.nombres} {self.apellidos or ''}"
        return strip_tags(name).strip()
    def get_nombre_completo(self):
        if self.nombre_empresa:
            return strip_tags(self.nombre_empresa)
        return strip_tags(f"{self.nombres} {self.apellidos or ''}").strip()
    
    get_full_name = get_nombre_completo
    get_nombre_completo.short_description = _('Nombre Completo')
    def calcular_cliente_frecuente(self, umbral_puntos=1000, umbral_compras=5):
        self.es_cliente_frecuente = self.puntos_fidelidad >= umbral_puntos
        return self.es_cliente_frecuente

    def get_fecha_ultima_compra(self):
        """Retorna la fecha de la última compra formateada o 'Sin compras'."""
        ultima_venta = self.ventas_asociadas.order_by('-fecha_venta').first()
        if ultima_venta:
            return ultima_venta.fecha_venta.strftime("%d %b %Y")
        return "Sin compras"

    @property
    def numero_documento(self):
        """Propiedad de compatibilidad para obtener el documento principal."""
        return self.cedula_identidad or self.numero_pasaporte or ''

    @property
    def telefono(self):
        """Propiedad de compatibilidad para obtener el teléfono principal."""
        return self.telefono_principal or ''

    def clean(self):
        if not self.nombre_empresa and (not self.nombres or not self.apellidos):
            raise ValidationError(_('Si no es una empresa, debe proporcionar nombres y apellidos.'))
        if self.email and Cliente.objects.filter(email=self.email).exclude(pk=self.pk).exists():
            raise ValidationError({'email': _('Ya existe un cliente con este correo electrónico.')})

from django.db import models
from django.utils.translation import gettext_lazy as _

from core.validators import validar_no_vacio_o_espacios


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
    codigo_iata = models.CharField(_("Código IATA"), max_length=3, blank=True, null=True, db_index=True, help_text=_("Código IATA de 3 letras de la ciudad o aeropuerto."))
    pais = models.ForeignKey(Pais, on_delete=models.PROTECT, verbose_name=_("País"), null=True, blank=True)
    region_estado = models.CharField(_("Región/Estado"), max_length=100, blank=True, null=True)
    
    class Meta:
        verbose_name = _("Ciudad")
        verbose_name_plural = _("Ciudades")
        ordering = ['pais__nombre', 'nombre']
        unique_together = ('nombre', 'pais', 'region_estado')

    def __str__(self):
        return f"{self.nombre}{f', {self.region_estado}' if self.region_estado else ''} ({self.pais.nombre})"

class Aerolinea(models.Model):
    id_aerolinea = models.AutoField(primary_key=True, verbose_name=_("ID Aerolínea"))
    codigo_iata = models.CharField(_("Código IATA"), max_length=3, blank=True, help_text=_("Código IATA de 2 letras de la aerolínea (ej. AA, AV, LA)."))
    codigo_numerico = models.CharField(_("Código Numérico/Placa"), max_length=3, blank=True, null=True, help_text=_("Código numérico de 3 dígitos asignado por IATA (ej. 134, 052)"))
    codigo_icao = models.CharField(_("Código ICAO"), max_length=3, blank=True, help_text=_("Código ICAO de 3 letras"))
    nombre = models.CharField(_("Nombre de la Aerolínea"), max_length=150, validators=[validar_no_vacio_o_espacios])
    orden_prioridad = models.IntegerField(_("Orden de Prioridad"), default=100, help_text=_("Para mostrar al principio en listas."))
    pais_origen = models.CharField(_("País de Origen"), max_length=100, blank=True)
    rif = models.CharField(_("RIF"), max_length=20, blank=True, help_text=_("RIF venezolano o E-99999999-X para internacionales"))
    activa = models.BooleanField(_("Activa"), default=True, help_text=_("Indica si la aerolínea está actualmente operando."))
    
    class Meta:
        verbose_name = _("Aerolínea")
        verbose_name_plural = _("Aerolíneas")
        ordering = ['nombre']
    
    def __str__(self):
        return f"{self.nombre} ({self.codigo_iata})"

"""Configuración del panel de administración para marketing.
"""

from django.contrib import admin

from core.api import SaaSAdminMixin

from .models import ActivoMarketing, Campania, ConfiguracionMarketing


@admin.register(Campania)
class CampaniaAdmin:
    """Configuración de administración para campania. Uso: instanciar según necesidad del dominio.
    """
    list_display = ("nombre", "estado", "fecha_inicio", "agencia")
    list_filter = ("estado", "agencia")
    search_fields = ("nombre", "descripcion")


@admin.register(ActivoMarketing)
class ActivoMarketingAdmin:
    """Configuración de administración para activomarketing. Uso: instanciar según necesidad del dominio.
    """
    list_display = ("tipo", "hotel", "campania", "generado_por_ia", "fecha_creacion")
    list_filter = ("tipo", "generado_por_ia")
    readonly_fields = ("fecha_creacion",)


@admin.register(ConfiguracionMarketing)
class ConfiguracionMarketingAdmin:
    """Configuración de administración para configuracionmarketing. Uso: instanciar según necesidad del dominio.
    """
    list_display = ("agencia", "color_primario", "color_secundario")

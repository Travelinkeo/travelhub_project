"""Configuración de la aplicación Django cotizaciones.
"""

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class CotizacionesConfig:
    """Configuración de cotizaciones. Uso: instanciar según necesidad del dominio.
    """
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.cotizaciones"
    verbose_name = _("Cotizaciones")

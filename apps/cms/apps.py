"""Configuración de la aplicación Django cms.
"""

from django.apps import AppConfig


class CmsConfig:
    """Configuración de cms. Uso: instanciar según necesidad del dominio.
    """
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.cms"

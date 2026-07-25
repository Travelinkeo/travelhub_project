"""Configuración de la aplicación Django common.
"""

from django.apps import AppConfig


class CommonConfig:
    """Configuración de common. Uso: instanciar según necesidad del dominio.
    """
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.common"

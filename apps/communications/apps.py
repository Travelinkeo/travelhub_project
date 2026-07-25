"""Configuración de la aplicación Django communications.
"""

from django.apps import AppConfig


class CommunicationsConfig:
    """Configuración de communications. Uso: instanciar según necesidad del dominio.
    """
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.communications"
    label = "communications"
    verbose_name = "Comunicaciones y Alertas"

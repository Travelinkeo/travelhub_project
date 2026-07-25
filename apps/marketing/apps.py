"""Configuración de la aplicación Django marketing.
"""

from django.apps import AppConfig


class MarketingConfig:
    """Configuración de marketing. Uso: instanciar según necesidad del dominio.
    """
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.marketing"
    verbose_name = "Marketing Automático"

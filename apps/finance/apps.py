"""Configuración de la aplicación Django finance.
"""

from django.apps import AppConfig


class FinanceConfig:
    """Configuración de finance. Uso: instanciar según necesidad del dominio.
    """
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.finance"
    label = "finance"
    verbose_name = "Finanzas y Facturación"

    def ready(self):
        # ready: Ready. Args: según implementación. Returns: según implementación.
        import apps.finance.receivers  # noqa: F401
        import apps.finance.signals  # noqa: F401

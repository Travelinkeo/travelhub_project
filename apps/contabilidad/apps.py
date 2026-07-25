# contabilidad/apps.py
"""Configuración de la aplicación Django contabilidad.
"""

from django.apps import AppConfig


class ContabilidadConfig:
    """Configuración de contabilidad. Uso: instanciar según necesidad del dominio.
    """
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.contabilidad"
    verbose_name = "Contabilidad VEN-NIF"

    def ready(self):
        # ready: Ready. Args: según implementación. Returns: según implementación.
        import apps.contabilidad.signals  # noqa: F401

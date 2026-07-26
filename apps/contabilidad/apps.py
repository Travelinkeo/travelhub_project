# contabilidad/apps.py
from django.apps import AppConfig


class ContabilidadConfig(AppConfig):
    """ContabilidadConfig."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.contabilidad"
    verbose_name = "Contabilidad VEN-NIF"

    def ready(self):
        """ready."""
        import apps.contabilidad.signals  # noqa: F401

# contabilidad/apps.py
from django.apps import AppConfig


class ContabilidadConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.contabilidad"
    verbose_name = "Contabilidad VEN-NIF"

    def ready(self):
        import apps.contabilidad.signals  # noqa: F401

from django.apps import AppConfig


class GamificationConfig(AppConfig):
    """GamificationConfig."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.gamification"
    verbose_name = "Gamificación"

    def ready(self):
        """ready."""
        # Importar signals para registrar los receivers (Venta, BoletoImportado,
        # Cliente, PagoVenta, Articulo). Sin esto el motor de logros nunca se dispara.
        from . import signals  # noqa: F401

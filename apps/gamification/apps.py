"""Configuración de la aplicación Django gamification.
"""

from django.apps import AppConfig


class GamificationConfig:
    """Configuración de gamification. Uso: instanciar según necesidad del dominio.
    """
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.gamification"
    verbose_name = "Gamificación"

    def ready(self):
        # ready: Ready. Args: según implementación. Returns: según implementación.
        import apps.gamification.signals

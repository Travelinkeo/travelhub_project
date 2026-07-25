"""Configuración de la aplicación Django bookings.
"""

from django.apps import AppConfig


class BookingsConfig:
    """Configuración de bookings. Uso: instanciar según necesidad del dominio.
    """
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.bookings"
    label = "bookings"
    verbose_name = "Reservas y Ventas (Bookings)"

    def ready(self):
        # ready: Ready. Args: según implementación. Returns: según implementación.
        import apps.bookings.signals  # noqa: F401
        import apps.bookings.tasks  # noqa: F401

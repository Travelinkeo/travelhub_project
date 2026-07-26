from django.apps import AppConfig


class BookingsConfig(AppConfig):
    """BookingsConfig."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.bookings"
    label = "bookings"
    verbose_name = "Reservas y Ventas (Bookings)"

    def ready(self):
        """ready."""
        import apps.bookings.signals  # noqa: F401
        import apps.bookings.tasks  # noqa: F401

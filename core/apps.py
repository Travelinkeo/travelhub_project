from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
    verbose_name = _('Núcleo de TravelHub')

    def ready(self):
        # Importar las señales para que se registren correctamente
        import core.services.parsing
        import core.signals  # noqa: F401

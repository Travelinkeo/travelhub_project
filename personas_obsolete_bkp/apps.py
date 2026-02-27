from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class PersonasConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'personas'
    verbose_name = _('Personas y Clientes')

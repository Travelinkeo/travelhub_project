from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class CotizacionesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'cotizaciones'
    verbose_name = _('Cotizaciones')

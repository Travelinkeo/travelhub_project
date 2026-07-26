from django.apps import AppConfig


class CrmConfig(AppConfig):
    """CrmConfig."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.crm"
    label = "crm"
    verbose_name = "CRM (Clientes y Pasajeros)"

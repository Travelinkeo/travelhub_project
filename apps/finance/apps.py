from django.apps import AppConfig


class FinanceConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.finance"
    label = "finance"
    verbose_name = "Finanzas y Facturación"

    def ready(self):
        import apps.finance.receivers  # noqa: F401
        import apps.finance.signals  # noqa: F401

from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'

    def ready(self):
        import core.signals  # noqa: F401
        import core.signals_audit  # noqa: F401
        import core.signals_passport  # noqa: F401
        import core.signals_contabilidad  # noqa: F401
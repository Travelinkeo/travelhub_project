from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"

    def ready(self):
        import core.signals  # noqa: F401
        import core.signals_audit  # noqa: F401
        import core.signals_passport  # noqa: F401
        from core.locale_patch import apply_locale_patch
        from core.services.agency_cache_service import setup_cache_signals

        # Aplicar el patch de locale al inicializar Django
        apply_locale_patch()

        setup_cache_signals()

        from django.db.models.signals import post_save

        from core.models import Agencia, UsuarioAgencia
        from core.security import _on_agencia_save, _on_usuario_agencia_save

        post_save.connect(
            _on_agencia_save, sender=Agencia, dispatch_uid="agencia_cache_invalidation"
        )
        post_save.connect(
            _on_usuario_agencia_save,
            sender=UsuarioAgencia,
            dispatch_uid="usuario_agencia_cache_invalidation",
        )

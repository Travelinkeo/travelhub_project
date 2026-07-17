"""Inicialización de TravelHub"""

try:
    from core.locale_patch import apply_locale_patch

    apply_locale_patch()
except ImportError:
    pass

# Cargar Celery app para que Django lo reconozca
try:
    from .celery import app as celery_app  # noqa: E402

    __all__ = ("celery_app",)
except ImportError:
    # Celery es opcional
    pass

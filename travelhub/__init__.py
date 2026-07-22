"""Inicialización de TravelHub"""

# Cargar Celery app para que Django lo reconozca
try:
    from .celery import app as celery_app  # noqa: E402

    __all__ = ("celery_app",)
except ImportError:
    # Celery es opcional
    pass

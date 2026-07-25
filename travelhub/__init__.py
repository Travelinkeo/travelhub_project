"""Inicialización de TravelHub — Configura la app Celery para que Django la reconozca al iniciar."""
try:
    from .celery import app as celery_app  # noqa: E402

    __all__ = ("celery_app",)
except ImportError:
    # Celery es opcional
    pass

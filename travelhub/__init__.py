"""Inicialización de TravelHub"""

# Cargar Celery app para que Django lo reconozca (Temporalmente desactivado por Code Freeze)
# try:
#     from .celery import app as celery_app
#     __all__ = ('celery_app',)
# except ImportError:
#     # Celery es opcional
#     pass

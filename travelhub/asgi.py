"""Punto de entrada ASGI para servidores asíncronos (Daphne, Uvicorn). Provee la aplicación ASGI de Django."""

import os

from django.core.asgi import get_asgi_application

# Configura el módulo de settings de Django antes de cargar la aplicación
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "travelhub.settings")
# Crea la aplicación ASGI
application = get_asgi_application()

"""Punto de entrada WSGI para servidores síncronos (Gunicorn). Configura encoding, telemetría y la app Django."""

import os

from django.core.wsgi import get_wsgi_application

# Fija encoding de PostgreSQL a UTF-8 en Windows/local
os.environ["PGCLIENTENCODING"] = "utf-8"

# Configura el módulo de settings de Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "travelhub.settings")

# Inicializa OpenTelemetry antes de cargar Django (requiere ENABLE_TELEMETRY=True en entorno)
from core.telemetry import setup_telemetry  # noqa: E402

setup_telemetry()

# Crea la aplicación WSGI
application = get_wsgi_application()

import os

from django.core.wsgi import get_wsgi_application

os.environ["PGCLIENTENCODING"] = "utf-8"

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "travelhub.settings")

# Inicializar OpenTelemetry antes de cargar Django (requiere ENABLE_TELEMETRY=True en entorno)
from core.telemetry import setup_telemetry  # noqa: E402

setup_telemetry()

application = get_wsgi_application()

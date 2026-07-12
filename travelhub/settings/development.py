"""
travelhub/settings/development.py
===================================
Configuración de DESARROLLO LOCAL.

Activa:
  - DEBUG = True
  - Email console
  - Django Debug Toolbar (si está instalada)
  - Query count middleware visible
  - Whitenoise autorefresh
  - Cookies sin HTTPS (desarrollo local)
  - Sentry desactivado

Uso:
  DJANGO_SETTINGS_MODULE=travelhub.settings.development
  (o simplemente no definir DJANGO_SETTINGS_MODULE — ver __init__.py)
"""

import os

from .base import *  # noqa: F401, F403
from .base import DEBUG, INSTALLED_APPS, MIDDLEWARE  # noqa: F401

__all__ = []

# ---------------------------------------------------------------------------
# Override DEBUG (permite forzar DEBUG=False en dev si se necesita)
# ---------------------------------------------------------------------------

# DEBUG ya viene de .env via base.py, pero en dev por defecto es True.
# Si el .env dice DEBUG=False, se respeta.

# ---------------------------------------------------------------------------
# Email: consola siempre en dev (sin importar RESEND_API_KEY)
# ---------------------------------------------------------------------------

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# ---------------------------------------------------------------------------
# Seguridad relajada para desarrollo local
# ---------------------------------------------------------------------------

SECURE_SSL_REDIRECT = False
X_FRAME_OPTIONS = "SAMEORIGIN"
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# Axes: deshabilitar en dev para no bloquear en desarrollo
AXES_ENABLED = os.getenv("AXES_ENABLED_DEV", "False").lower() == "true"

# ---------------------------------------------------------------------------
# Whitenoise
# ---------------------------------------------------------------------------

WHITENOISE_AUTOREFRESH = True

# ---------------------------------------------------------------------------
# Django Debug Toolbar (opcional, instalar con: pip install django-debug-toolbar)
# ---------------------------------------------------------------------------

if os.getenv("ENABLE_DEBUG_TOOLBAR", "False").lower() == "true":
    try:
        import debug_toolbar  # noqa: F401

        INSTALLED_APPS = [*INSTALLED_APPS, "debug_toolbar"]
        MIDDLEWARE = [
            "debug_toolbar.middleware.DebugToolbarMiddleware",
            *MIDDLEWARE,
        ]
        INTERNAL_IPS = ["127.0.0.1", "localhost"]
        DEBUG_TOOLBAR_CONFIG = {
            "SHOW_COLLAPSED": True,
            "ENABLE_STACKTRACES": True,
        }
    except ImportError:
        pass

# ---------------------------------------------------------------------------
# Sentry: desactivado en desarrollo
# ---------------------------------------------------------------------------

SENTRY_DSN = ""

# ---------------------------------------------------------------------------
# Logging en desarrollo: más verbose
# ---------------------------------------------------------------------------

import logging  # noqa: E402

logging.getLogger("django.db.backends").setLevel(
    logging.DEBUG if os.getenv("LOG_SQL", "False").lower() == "true" else logging.WARNING
)

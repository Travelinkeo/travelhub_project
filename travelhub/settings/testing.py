"""
travelhub/settings/testing.py
==============================
Configuración de TEST (pytest / CI).

Activa:
  - Email en memoria (locmem)
  - Celery en modo eager (síncrono, sin workers)
  - Cache en memoria (sin Redis)
  - Storage local (sin R2)
  - Axes deshabilitado
  - Sentry desactivado
  - Contraseñas hasheadas con MD5 (más rápido en tests)
  - Sin migraciones pesadas (usa DJNAGO_TESTING=True flag)

Uso:
  DJANGO_SETTINGS_MODULE=travelhub.settings.testing
  # o en pytest.ini / conftest.py:
  #   django_settings_module = travelhub.settings.testing
"""

from .base import *  # noqa: F401, F403
from .base import STORAGES  # noqa: F401

__all__ = []

# ---------------------------------------------------------------------------
# Forzar DEBUG=False en tests para detectar errores de producción
# ---------------------------------------------------------------------------

DEBUG = False

# ---------------------------------------------------------------------------
# Email: en memoria (sin envíos reales)
# ---------------------------------------------------------------------------

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# ---------------------------------------------------------------------------
# Celery: modo síncrono (sin workers externos)
# ---------------------------------------------------------------------------

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# ---------------------------------------------------------------------------
# Storage: FileSystem local (sin R2)
# ---------------------------------------------------------------------------

STORAGES["default"] = {"BACKEND": "django.core.files.storage.FileSystemStorage"}

# Sin R2 en tests: RawFileStorage (core/storage.py) cae a FileSystemStorage local
# y evita llamadas a S3/botocore que no existen en el entorno de CI.
USE_R2 = False

# ---------------------------------------------------------------------------
# Cache: en memoria (sin Redis)
# ---------------------------------------------------------------------------

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "test-cache",
    }
}

# ---------------------------------------------------------------------------
# Sesiones: en base de datos (sin Redis en CI)
# ---------------------------------------------------------------------------

SESSION_ENGINE = "django.contrib.sessions.backends.db"

# ---------------------------------------------------------------------------
# Seguridad relajada para tests
# ---------------------------------------------------------------------------

SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# ---------------------------------------------------------------------------
# Axes: deshabilitado en tests (no bloquear IPs en CI)
# ---------------------------------------------------------------------------

AXES_ENABLED = False

# ---------------------------------------------------------------------------
# Sentry: desactivado en tests
# ---------------------------------------------------------------------------

SENTRY_DSN = ""

# ---------------------------------------------------------------------------
# Passwords: usar MD5 hasher (mucho más rápido en tests)
# ---------------------------------------------------------------------------

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# ---------------------------------------------------------------------------
# Logging: silenciar warnings innecesarios en tests
# ---------------------------------------------------------------------------

import logging  # noqa: E402

logging.disable(logging.CRITICAL)

# ---------------------------------------------------------------------------
# Criptografía: Clave estática Fernet válida para tests unitarios
# ---------------------------------------------------------------------------
ENCRYPTION_KEY = "ujK9r7o7B-B-jH87L2K0XvB4oK9zB_M3_z6vG1T_P5U="

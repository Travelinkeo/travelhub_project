"""
Settings para tests de integración.
Hereda de settings.py de producción pero fuerza SQLite en memoria
para que los tests sean rápidos, aislados y no requieran Docker.
"""
from travelhub.settings import *  # noqa: F401, F403

# --- Base de datos en memoria para tests ---
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# --- Celery síncrono para tests ---
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = False

# --- Deshabilitar caché real ---
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

# --- Storage local para tests (sin Cloudflare R2) ---
DEFAULT_FILE_STORAGE = "django.core.files.storage.FileSystemStorage"
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}

# --- Email dummy ---
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# --- Desactivar Gemini real (los tests deben mockearlo) ---
GEMINI_API_KEY = "fake-test-key-do-not-use"
GOOGLE_API_KEY = "fake-test-key-do-not-use"

# --- Silenciar logs en tests ---
LOGGING = {
    "version": 1,
    "disable_existing_loggers": True,
    "handlers": {"null": {"class": "logging.NullHandler"}},
    "root": {"handlers": ["null"]},
}

# --- Password hasher rápido ---
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# --- Deshabilitar migraciones para tests (crea tablas directamente) ---
class DisableMigrations(dict):
    def __contains__(self, item):
        return True
    def __getitem__(self, item):
        return None

MIGRATION_MODULES = DisableMigrations()


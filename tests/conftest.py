import os
import pytest

# Asegurar configuración de Django incluso si pytest-django no se auto-carga
if 'DJANGO_SETTINGS_MODULE' not in os.environ:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
try:
    import django  # noqa: E402
    from django.conf import settings  # noqa: E402
    if not settings.configured:  # pragma: no cover
        django.setup()
except Exception:  # pragma: no cover
    # Si falla aquí, los tests fallarán luego con más contexto; evitamos romper import global.
    pass

@pytest.fixture(autouse=True)
def use_simple_static_storage(settings):
    # Evita errores de ManifestStaticFilesStorage en tests sin collectstatic
    settings.STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'
    # En caso de que whitenoise se apoye en finders
    settings.WHITENOISE_USE_FINDERS = True

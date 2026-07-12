"""
travelhub/settings/__init__.py
================================
Router automático de configuración.

Selecciona el módulo de settings correcto según la variable de entorno
DJANGO_ENV (o ENVIRONMENT). Si ya existe DJANGO_SETTINGS_MODULE definida
explícitamente, este archivo no interfiere.

  DJANGO_ENV=production  → travelhub.settings.production
  DJANGO_ENV=development → travelhub.settings.development (default)
  DJANGO_ENV=testing     → travelhub.settings.testing

Para compatibilidad total con el settings.py monolítico anterior,
este __init__.py re-exporta todo desde el módulo seleccionado.
Esto significa que `travelhub.settings` sigue siendo una referencia válida.

Ejemplos de uso:
  # Docker / Render (producción)
  DJANGO_SETTINGS_MODULE=travelhub.settings.production

  # Docker Compose local
  DJANGO_SETTINGS_MODULE=travelhub.settings.development

  # pytest (en pytest.ini o conftest.py)
  DJANGO_SETTINGS_MODULE=travelhub.settings.testing
"""

import os

# Este __init__.py solo actúa como guía de documentación.
# La selección real la hace DJANGO_SETTINGS_MODULE en el entorno.
# Si alguien importa `travelhub.settings` directamente (sin submodule),
# cargamos el módulo apropiado automáticamente.

_env = os.environ.get("DJANGO_ENV", os.environ.get("ENVIRONMENT", "development")).lower()

if _env == "production":
    from .production import *  # noqa: F401, F403
elif _env in ("test", "testing", "ci"):
    from .testing import *  # noqa: F401, F403
else:
    # development (default)
    from .development import *  # noqa: F401, F403

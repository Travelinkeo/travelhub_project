"""
Router automático de configuración según DJANGO_ENV.

Selecciona el módulo de settings (production/development/testing) basado en
la variable de entorno DJANGO_ENV (o ENVIRONMENT como fallback).
Permite que `travelhub.settings` como referencia siga funcionando.
"""

import os

# Lee DJANGO_ENV o ENVIRONMENT del entorno; default development
_env = os.environ.get("DJANGO_ENV", os.environ.get("ENVIRONMENT", "development")).lower()

if _env == "production":
    from .production import *  # noqa: F401, F403
elif _env in ("test", "testing", "ci"):
    from .testing import *  # noqa: F401, F403
else:
    # development (default)
    from .development import *  # noqa: F401, F403

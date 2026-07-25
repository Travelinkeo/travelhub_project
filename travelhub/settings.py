"""
travelhub/settings.py — COMPATIBILIDAD (DEPRECADO)
====================================================
⚠️ Este archivo es un shim de compatibilidad temporal.

La configuración real ahora vive en travelhub/settings/:
  - settings/base.py        → Configuración base compartida
  - settings/production.py  → Producción (HSTS, Sentry, seguridad)
  - settings/development.py → Desarrollo local (DEBUG, toolbar)
  - settings/testing.py     → Tests (eager Celery, MD5 hasher)

Para usar el nuevo sistema, cambia DJANGO_SETTINGS_MODULE en tu entorno:
  Producción:  DJANGO_SETTINGS_MODULE=travelhub.settings.production
  Desarrollo:  DJANGO_SETTINGS_MODULE=travelhub.settings.development
  Tests:       DJANGO_SETTINGS_MODULE=travelhub.settings.testing

Este archivo (settings.py) se mantiene para compatibilidad con herramientas
que buscan travelhub/settings.py. Redirige automáticamente al paquete.
Eliminarlo es seguro una vez que DJANGO_SETTINGS_MODULE esté actualizado
en todos los entornos (Docker, CI, Render, etc.).
"""

# Re-exporta todo desde el paquete de settings (selecciona según DJANGO_ENV)
from travelhub.settings import *  # noqa: F401, F403

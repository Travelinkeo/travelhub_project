"""
travelhub/settings/production.py
=================================
Configuración de PRODUCCIÓN.

Activa:
  - HSTS + SSL redirect
  - Cookies seguras (HTTPS-only)
  - Sentry error tracking
  - Validaciones estrictas de variables críticas
  - Cloudflare R2 (ya activado en base si USE_R2=True)
  - Seguridad HTTP headers estricta

Uso:
  DJANGO_SETTINGS_MODULE=travelhub.settings.production
"""

import os

from .base import *  # noqa: F401, F403
from .base import DEBUG, ENCRYPTION_KEY, SECRET_KEY, SENTRY_DSN  # noqa: F401

# ---------------------------------------------------------------------------
# Validaciones de producción — falla rápido si falta algo crítico
# ---------------------------------------------------------------------------

if len(SECRET_KEY) < 50:
    from django.core.exceptions import ImproperlyConfigured

    raise ImproperlyConfigured("🔒 SECRET_KEY debe tener al menos 50 caracteres en producción")

if not ENCRYPTION_KEY:
    from django.core.exceptions import ImproperlyConfigured

    raise ImproperlyConfigured("ENCRYPTION_KEY debe configurarse en producción")

if ENCRYPTION_KEY and len(ENCRYPTION_KEY) < 32:
    from django.core.exceptions import ImproperlyConfigured

    raise ImproperlyConfigured("ENCRYPTION_KEY debe tener al menos 32 caracteres")

try:
    from cryptography.fernet import Fernet

    Fernet(ENCRYPTION_KEY.encode() if isinstance(ENCRYPTION_KEY, str) else ENCRYPTION_KEY)
except Exception:
    from django.core.exceptions import ImproperlyConfigured

    raise ImproperlyConfigured(
        "ENCRYPTION_KEY no es una clave Fernet válida. "
        'Genera una con: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"'
    ) from None

if not os.getenv("WHATSAPP_MICROSERVICE_TOKEN"):
    from django.core.exceptions import ImproperlyConfigured

    raise ImproperlyConfigured("WHATSAPP_MICROSERVICE_TOKEN debe configurarse en producción")

if not os.getenv("EVOLUTION_INSTANCE_TOKEN"):
    from django.core.exceptions import ImproperlyConfigured

    raise ImproperlyConfigured("EVOLUTION_INSTANCE_TOKEN debe configurarse en producción")

# ---------------------------------------------------------------------------
# Sentry — inicialización no bloqueante
# ---------------------------------------------------------------------------

SENTRY_ENVIRONMENT = os.getenv("ENVIRONMENT", "production")
SENTRY_RELEASE = os.getenv("GIT_SHA", "unknown")

if SENTRY_DSN and SENTRY_DSN.startswith("http"):
    import threading as _sentry_thread

    def _init_sentry():
        """_init_sentry."""
        import sentry_sdk as _sdk
        from sentry_sdk.integrations.celery import CeleryIntegration as _CeleryInt
        from sentry_sdk.integrations.django import DjangoIntegration as _DjangoInt
        from sentry_sdk.integrations.redis import RedisIntegration as _RedisInt

        _sdk.init(
            dsn=SENTRY_DSN,
            environment=SENTRY_ENVIRONMENT,
            release=SENTRY_RELEASE,
            integrations=[_DjangoInt(), _CeleryInt(), _RedisInt()],
            traces_sample_rate=0.1,
            profiles_sample_rate=0.01,
        )

    _sentry_thread.Thread(target=_init_sentry, daemon=True).start()

# ---------------------------------------------------------------------------
# HTTP Security — solo en producción
# ---------------------------------------------------------------------------

# SSL redirect controlado por env var (default False para acceso directo al puerto 8000
# cuando hay proxy/Cloudflare delante con SSL)
from .base import env  # noqa: E402

SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", False)

# Aceptar X-Forwarded-Proto de Traefik/Cloudflare; sin proxy eliminar este setting.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# HSTS: Decirle al browser que SOLO use HTTPS por 1 año
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Protección contra clickjacking
X_FRAME_OPTIONS = "DENY"

# Prevenir que el browser "olfatee" el tipo de contenido
SECURE_CONTENT_TYPE_NOSNIFF = True

# Cookies solo por HTTPS
SESSION_COOKIE_SECURE = env.bool("SESSION_COOKIE_SECURE", True)
CSRF_COOKIE_SECURE = env.bool("CSRF_COOKIE_SECURE", True)

# ---------------------------------------------------------------------------
# Whitenoise: sin autorefresh en producción
# ---------------------------------------------------------------------------

WHITENOISE_AUTOREFRESH = False

# ---------------------------------------------------------------------------
# Binance: warning si no está configurado (no bloquea)
# ---------------------------------------------------------------------------

import logging as _log  # noqa: E402

_logger = _log.getLogger(__name__)
if not os.getenv("BINANCE_PAY_API_KEY"):
    _logger.warning("⚠️ BINANCE_PAY_API_KEY no configurado — pagos vía Binance deshabilitados.")

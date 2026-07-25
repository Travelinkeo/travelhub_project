import logging
import os

from django.core.cache import cache

logger = logging.getLogger(__name__)

CACHE_TTL = 300  # 5 minutos


def _get_from_cache(service: str) -> str | None:
    """Lee de caché Redis"""
    return cache.get(f"api_secret:{service}")


def _set_cache(service: str, value: str) -> None:
    """Función interna: set cache."""
    cache.set(f"api_secret:{service}", value, CACHE_TTL)


def get_api_secret(service: str, default: str | None = None) -> str | None:
    """
    Obtiene el valor de una clave API con cadencia de resolución:
    1. Caché Redis (rápido, evita golpear DB)
    2. DB (APISecret) — encriptado, se descifra automáticamente
    3. Variable de entorno (os.getenv) — fallback legacy
    4. default proporcionado

    Uso:
        GEMINI_API_KEY = get_api_secret("GEMINI_API_KEY", "")
        STRIPE_SECRET_KEY = get_api_secret("STRIPE_SECRET_KEY")
    """
    # 1. Caché
    cached = _get_from_cache(service)
    if cached is not None:
        return cached

    # 2. DB (lazy import para evitar circular)
    try:
        from core.models import APISecret

        obj = APISecret.objects.filter(service=service, is_active=True).first()
        if obj and obj.value:
            _set_cache(service, obj.value)
            return obj.value
    except Exception as e:
        logger.debug("APISecret DB lookup failed for %s: %s", service, e)

    # 3. Env var (fallback legacy)
    env_val = os.getenv(service)
    if env_val:
        _set_cache(service, env_val)
        return env_val

    # 4. Default
    return default

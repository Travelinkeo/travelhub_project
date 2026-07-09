"""
Rate limiter por plan usando Redis.

Implementa un sliding window counter por API key.
Si Redis no está disponible, permite el request (fail-open).
"""

import logging

from django.conf import settings

logger = logging.getLogger(__name__)

# Redis connection (lazy)
_redis_client = None


def _get_redis():
    """Obtiene conexión Redis (lazy, con fallback)."""
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    try:
        import redis

        redis_url = getattr(settings, "REDIS_CACHE_URL", None) or getattr(
            settings, "CACHES", {}
        ).get("default", {}).get("LOCATION", "redis://localhost:6379/0")
        _redis_client = redis.from_url(redis_url, socket_timeout=2)
        _redis_client.ping()
        return _redis_client
    except Exception as e:
        logger.debug(f"Redis no disponible para rate limiting: {e}")
        _redis_client = False  # Marcar como no disponible
        return None


def check_rate_limit(api_key) -> tuple[bool, int]:
    """
    Verifica si la API key excedió su rate limit.

    Returns:
        (allowed, remaining): allowed=True si puede hacer el request,
        remaining=requests restantes en la ventana actual.
    """
    redis_client = _get_redis()
    if redis_client is None or redis_client is False:
        # Fail-open: si Redis no está disponible, permitir
        return True, api_key.rate_limit

    try:
        key = f"rate_limit:api:{api_key.key_hash[:16]}"
        window = 3600  # 1 hora en segundos
        limit = api_key.rate_limit

        # Sliding window counter con pipeline
        pipe = redis_client.pipeline()
        now = __import__("time").time()

        # Limpiar entries fuera de la ventana
        pipe.zremrangebyscore(key, 0, now - window)
        # Contar requests en la ventana actual
        pipe.zcard(key)
        # Agregar el request actual
        pipe.zadd(key, {f"{now}": now})
        # TTL para auto-limpieza
        pipe.expire(key, window + 60)

        results = pipe.execute()
        current_count = results[1]  # zcard resultado

        remaining = max(0, limit - current_count - 1)
        allowed = current_count < limit

        if not allowed:
            logger.warning(
                f"Rate limit excedido para API key {api_key.prefix}... "
                f"({current_count}/{limit} en ventana de 1h)"
            )

        return allowed, remaining

    except Exception as e:
        logger.debug(f"Error en rate limiting: {e}")
        return True, api_key.rate_limit


def get_rate_limit_headers(api_key) -> dict:
    """Genera headers de rate limit para la respuesta HTTP."""
    return {
        "X-RateLimit-Limit": str(api_key.rate_limit),
        "X-RateLimit-Plan": api_key.plan,
        "X-RateLimit-Remaining": str(getattr(api_key, "_remaining", api_key.rate_limit)),
    }

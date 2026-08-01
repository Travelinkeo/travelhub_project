# core/cache.py
import hashlib
import json
import logging
from functools import wraps

from django.core.cache import cache

logger = logging.getLogger(__name__)


def cache_api_response(timeout=300, key_prefix="api"):
    """
    Decorator para cachear respuestas de API.

    Args:
        timeout: Tiempo en segundos (default 5 minutos)
        key_prefix: Prefijo para la clave de caché
    """

    def decorator(func):
        """decorator."""

        @wraps(func)
        def wrapper(request, *args, **kwargs):
            """wrapper."""
            # Solo cachear GET requests
            if request.method != "GET":
                return func(request, *args, **kwargs)

            # Generar clave única basada en URL y query params
            cache_key_data = {
                "path": request.path,
                "query": dict(request.GET),
                "user": request.user.id if request.user.is_authenticated else None,
            }
            cache_key_hash = hashlib.sha256(
                json.dumps(cache_key_data, sort_keys=True).encode()
            ).hexdigest()[:32]
            cache_key = f"{key_prefix}:{cache_key_hash}"

            # Intentar obtener del caché
            cached_data = cache.get(cache_key)
            if cached_data is not None:
                from rest_framework.response import Response

                return Response(cached_data)

            # Ejecutar función y cachear resultado
            response = func(request, *args, **kwargs)

            # Cachear solo los datos, no el objeto Response
            if hasattr(response, "data"):
                cache.set(cache_key, response.data, timeout)

            return response

        return wrapper

    return decorator


def invalidate_cache_pattern(pattern):
    """
    Invalida todas las claves de caché que coincidan con un patrón.
    Requiere Redis como backend.
    Usa SCAN en lugar de KEYS para no bloquear Redis en producción.
    """
    try:
        from django_redis import get_redis_connection

        conn = get_redis_connection("default")
        cursor = 0
        deleted = 0
        while True:
            cursor, keys = conn.scan(cursor, match=f"*{pattern}*", count=100)
            if keys:
                conn.delete(*keys)
                deleted += len(keys)
            if cursor == 0:
                break
        logger.info(f"Invalidated {deleted} cache keys matching pattern: {pattern}")
    except ImportError:
        # Si no está Redis, limpiar todo el caché
        cache.clear()

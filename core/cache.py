# core/cache.py
from functools import wraps
from django.core.cache import cache
from django.conf import settings
import hashlib
import json


def cache_api_response(timeout=300, key_prefix='api'):
    """
    Decorator para cachear respuestas de API.
    
    Args:
        timeout: Tiempo en segundos (default 5 minutos)
        key_prefix: Prefijo para la clave de caché
    """
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            # Solo cachear GET requests
            if request.method != 'GET':
                return func(request, *args, **kwargs)
            
            # Generar clave única basada en URL y query params
            cache_key_data = {
                'path': request.path,
                'query': dict(request.GET),
                'user': request.user.id if request.user.is_authenticated else None
            }
            cache_key_hash = hashlib.md5(
                json.dumps(cache_key_data, sort_keys=True).encode()
            ).hexdigest()
            cache_key = f'{key_prefix}:{cache_key_hash}'
            
            # Intentar obtener del caché
            cached_data = cache.get(cache_key)
            if cached_data is not None:
                from rest_framework.response import Response
                return Response(cached_data)
            
            # Ejecutar función y cachear resultado
            response = func(request, *args, **kwargs)
            
            # Cachear solo los datos, no el objeto Response
            if hasattr(response, 'data'):
                cache.set(cache_key, response.data, timeout)
            
            return response
        return wrapper
    return decorator


def invalidate_cache_pattern(pattern):
    """
    Invalida todas las claves de caché que coincidan con un patrón.
    Requiere Redis como backend.
    """
    try:
        from django_redis import get_redis_connection
        conn = get_redis_connection("default")
        keys = conn.keys(f'*{pattern}*')
        if keys:
            conn.delete(*keys)
    except ImportError:
        # Si no está Redis, limpiar todo el caché
        cache.clear()

"""Utilidades de caché para optimizar rendimiento"""
from django.core.cache import cache
from functools import wraps
import logging

logger = logging.getLogger(__name__)


def cache_queryset(timeout=3600, key_prefix=''):
    """
    Decorator para cachear resultados de querysets.
    
    Args:
        timeout: Tiempo en segundos (default: 1 hora)
        key_prefix: Prefijo para la clave de caché
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Construir clave de caché
            cache_key = f"{key_prefix}:{func.__name__}"
            if args:
                cache_key += f":{':'.join(str(arg) for arg in args[1:])}"
            if kwargs:
                cache_key += f":{':'.join(f'{k}={v}' for k, v in sorted(kwargs.items()))}"
            
            # Intentar obtener del caché
            result = cache.get(cache_key)
            if result is not None:
                logger.debug(f"Cache HIT: {cache_key}")
                return result
            
            # Si no está en caché, ejecutar función
            logger.debug(f"Cache MISS: {cache_key}")
            result = func(*args, **kwargs)
            
            # Guardar en caché
            cache.set(cache_key, result, timeout)
            return result
        
        return wrapper
    return decorator


def invalidate_cache(key_pattern):
    """Invalida caché por patrón de clave"""
    try:
        cache.delete_pattern(key_pattern)
        logger.info(f"Cache invalidado: {key_pattern}")
    except Exception as e:
        logger.warning(f"No se pudo invalidar caché: {e}")

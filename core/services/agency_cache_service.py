"""
Servicio de caching para sesiones de agencias.
Optimiza el acceso a datos de agencia usando Redis cache.
"""
import logging
from typing import Any, Optional

from django.core.cache import cache
from django.db import models

logger = logging.getLogger(__name__)

# Constantes de cache
AGENCIA_CACHE_TIMEOUT = 3600  # 1 hora
AGENCIA_CACHE_PREFIX = "agencia"
USUARIO_AGENCIAS_CACHE_TIMEOUT = 1800  # 30 minutos
USUARIO_AGENCIAS_CACHE_PREFIX = "usuario_agencias"


def _make_cache_key(prefix: str, identifier: str) -> str:
    """Genera una clave de cache única."""
    return f"th:{prefix}:{identifier}"


def get_agencia_from_cache(agencia_id: int) -> Optional[dict]:
    """
    Obtiene datos de agencia desde cache.
    Si no existe en cache, lo consulta y lo almacena.
    """
    cache_key = _make_cache_key(AGENCIA_CACHE_PREFIX, str(agencia_id))
    
    try:
        data = cache.get(cache_key)
        if data is not None:
            return data
            
        # Cache miss - consultar BD
        from core.models import Agencia
        agencia = Agencia.objects.filter(pk=agencia_id).first()
        
        if agencia:
            data = {
                'id': agencia.pk,
                'nombre': agencia.nombre,
                'activo': agencia.activa,
                'plan': getattr(agencia, 'plan', None),
            }
            cache.set(cache_key, data, AGENCIA_CACHE_TIMEOUT)
            return data
            
        return None
    except Exception as e:
        logger.warning(f"Error en cache de agencia {agencia_id}: {e}")
        return None


def invalidate_agencia_cache(agencia_id: int) -> bool:
    """Invalida el cache de una agencia específica."""
    cache_key = _make_cache_key(AGENCIA_CACHE_PREFIX, str(agencia_id))
    try:
        cache.delete(cache_key)
        return True
    except Exception as e:
        logger.warning(f"Error invalidando cache de agencia {agencia_id}: {e}")
        return False


def get_usuario_agencias_from_cache(user_id: int) -> list:
    """
    Obtiene las agencias asociadas a un usuario desde cache.
    """
    cache_key = _make_cache_key(USUARIO_AGENCIAS_CACHE_PREFIX, str(user_id))
    
    try:
        data = cache.get(cache_key)
        if data is not None:
            return data
            
        # Cache miss - consultar BD
        try:
            from core.models import UsuarioAgencia
            usuario_agencias = list(
                UsuarioAgencia.objects.filter(
                    usuario_id=user_id,
                    activo=True
                ).select_related('agencia').values_list('agencia_id', flat=True)
            )
            
            cache.set(cache_key, usuario_agencias, USUARIO_AGENCIAS_CACHE_TIMEOUT)
            return usuario_agencias
        except Exception:
            return []
    except Exception as e:
        logger.warning(f"Error en cache de usuario_agencias {user_id}: {e}")
        return []


def invalidate_usuario_agencias_cache(user_id: int) -> bool:
    """Invalida el cache de agencias de un usuario."""
    cache_key = _make_cache_key(USUARIO_AGENCIAS_CACHE_PREFIX, str(user_id))
    try:
        cache.delete(cache_key)
        return True
    except Exception as e:
        logger.warning(f"Error invalidando cache de usuario_agencias {user_id}: {e}")
        return False


def cache_agencia_dashboard_data(agencia_id: int, data: dict, timeout: int = 300) -> bool:
    """
    Cachea datos del dashboard de una agencia.
    Timeout por defecto: 5 minutos.
    """
    cache_key = _make_cache_key(f"{AGENCIA_CACHE_PREFIX}_dashboard", str(agencia_id))
    try:
        cache.set(cache_key, data, timeout)
        return True
    except Exception as e:
        logger.warning(f"Error cacheando dashboard de agencia {agencia_id}: {e}")
        return False


def get_agencia_dashboard_data(agencia_id: int) -> Optional[dict]:
    """Obtiene datos del dashboard cacheados de una agencia."""
    cache_key = _make_cache_key(f"{AGENCIA_CACHE_PREFIX}_dashboard", str(agencia_id))
    try:
        return cache.get(cache_key)
    except Exception as e:
        logger.warning(f"Error obteniendo dashboard cacheado de agencia {agencia_id}: {e}")
        return None


def cache_query_result(cache_key: str, data: Any, timeout: int = 300) -> bool:
    """
    Cachea el resultado de una query genérica.
    """
    try:
        cache.set(cache_key, data, timeout)
        return True
    except Exception as e:
        logger.warning(f"Error cacheando query {cache_key}: {e}")
        return False


def get_cached_query_result(cache_key: str) -> Any:
    """Obtiene el resultado cacheado de una query."""
    try:
        return cache.get(cache_key)
    except Exception as e:
        logger.warning(f"Error obteniendo query cacheada {cache_key}: {e}")
        return None


def invalidate_pattern(pattern: str) -> int:
    """
    Invalida todas las claves de cache que coinciden con un patrón.
    Nota: Esto usa key iteration que puede ser lento en producción con muchas claves.
    """
    try:
        from django.core.cache import caches
        default_cache = caches['default']
        
        # django-redis soporta delete_pattern
        if hasattr(default_cache, 'delete_pattern'):
            return default_cache.delete_pattern(pattern)
        
        return 0
    except Exception as e:
        logger.warning(f"Error invalidando patrón {pattern}: {e}")
        return 0


# Signals para invalidar cache automáticamente
def setup_cache_signals():
    """Configura signals para invalidar cache cuando se modifican modelos relevantes."""
    from django.db.models.signals import post_save, post_delete
    from django.dispatch import receiver
    
    @receiver(post_save, sender='core.Agencia')
    def invalidate_agencia_on_save(sender, instance, **kwargs):
        invalidate_agencia_cache(instance.pk)
        logger.debug(f"Cache invalidado para agencia {instance.pk}")
    
    @receiver(post_delete, sender='core.Agencia')
    def invalidate_agencia_on_delete(sender, instance, **kwargs):
        invalidate_agencia_cache(instance.pk)
        logger.debug(f"Cache invalidado para agencia eliminada {instance.pk}")
    
    @receiver(post_save, sender='core.UsuarioAgencia')
    def invalidate_usuario_agencias_on_save(sender, instance, **kwargs):
        invalidate_usuario_agencias_cache(instance.usuario_id)
        logger.debug(f"Cache invalidado para usuario_agencias de usuario {instance.usuario_id}")
    
    @receiver(post_delete, sender='core.UsuarioAgencia')
    def invalidate_usuario_agencias_on_delete(sender, instance, **kwargs):
        invalidate_usuario_agencias_cache(instance.usuario_id)
        logger.debug(f"Cache invalidado para usuario_agencias eliminado de usuario {instance.usuario_id}")

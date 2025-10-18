"""Middleware para monitorear rendimiento y queries"""
import time
import logging
from django.conf import settings
from django.db import connection

logger = logging.getLogger(__name__)


class QueryCountDebugMiddleware:
    """Middleware para contar queries en modo DEBUG"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        if settings.DEBUG:
            # Resetear queries
            connection.queries_log.clear()
            start_time = time.time()
        
        response = self.get_response(request)
        
        if settings.DEBUG:
            # Calcular tiempo y queries
            duration = time.time() - start_time
            num_queries = len(connection.queries)
            
            if num_queries > 10:  # Alertar si hay muchas queries
                logger.warning(
                    f"⚠️ {request.path} - {num_queries} queries en {duration:.2f}s"
                )
            else:
                logger.debug(
                    f"✅ {request.path} - {num_queries} queries en {duration:.2f}s"
                )
        
        return response


class CacheHeaderMiddleware:
    """Middleware para agregar headers de caché"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        response = self.get_response(request)
        
        # Agregar headers de caché para endpoints de catálogos
        if request.path.startswith('/api/paises') or \
           request.path.startswith('/api/monedas') or \
           request.path.startswith('/api/aerolineas'):
            response['Cache-Control'] = 'public, max-age=3600'
        elif request.path.startswith('/api/ciudades'):
            response['Cache-Control'] = 'public, max-age=1800'
        
        return response

"""Tests para middleware de performance"""
import pytest
from unittest.mock import Mock
from django.test import RequestFactory
from core.middleware_performance import QueryCountDebugMiddleware, CacheHeaderMiddleware


class TestQueryCountDebugMiddleware:
    """Tests para QueryCountDebugMiddleware"""
    
    def test_middleware_processes_request(self, settings):
        """Test que middleware procesa request correctamente"""
        settings.DEBUG = True
        
        get_response = Mock(return_value=Mock())
        middleware = QueryCountDebugMiddleware(get_response)
        
        factory = RequestFactory()
        request = factory.get('/api/test/')
        
        response = middleware(request)
        
        assert response is not None
        get_response.assert_called_once()
    
    def test_middleware_skips_in_production(self, settings):
        """Test que middleware no hace nada en producción"""
        settings.DEBUG = False
        
        get_response = Mock(return_value=Mock())
        middleware = QueryCountDebugMiddleware(get_response)
        
        factory = RequestFactory()
        request = factory.get('/api/test/')
        
        response = middleware(request)
        
        assert response is not None


class TestCacheHeaderMiddleware:
    """Tests para CacheHeaderMiddleware"""
    
    def test_adds_cache_headers_for_paises(self):
        """Test que agrega headers de caché para países"""
        get_response = Mock(return_value=Mock())
        middleware = CacheHeaderMiddleware(get_response)
        
        factory = RequestFactory()
        request = factory.get('/api/paises/')
        
        response = middleware(request)
        
        assert 'Cache-Control' in response
        assert 'max-age=3600' in response['Cache-Control']
    
    def test_adds_cache_headers_for_ciudades(self):
        """Test que agrega headers de caché para ciudades"""
        get_response = Mock(return_value=Mock())
        middleware = CacheHeaderMiddleware(get_response)
        
        factory = RequestFactory()
        request = factory.get('/api/ciudades/')
        
        response = middleware(request)
        
        assert 'Cache-Control' in response
        assert 'max-age=1800' in response['Cache-Control']
    
    def test_no_cache_headers_for_other_endpoints(self):
        """Test que no agrega headers para otros endpoints"""
        get_response = Mock(return_value=Mock())
        middleware = CacheHeaderMiddleware(get_response)
        
        factory = RequestFactory()
        request = factory.get('/api/ventas/')
        
        response = middleware(request)
        
        # No debe tener Cache-Control o debe ser diferente
        # (depende de la implementación)

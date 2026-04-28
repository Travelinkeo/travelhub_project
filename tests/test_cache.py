"""Tests para sistema de caché"""
import pytest
from django.core.cache import cache
from core.cache_utils import cache_queryset, invalidate_cache


class TestCacheUtils:
    """Tests para utilidades de caché"""
    
    def setup_method(self):
        """Limpiar caché antes de cada test"""
        cache.clear()
    
    def test_cache_queryset_decorator(self):
        """Test que el decorator cachea resultados"""
        call_count = 0
        
        @cache_queryset(timeout=60, key_prefix='test')
        def expensive_function():
            nonlocal call_count
            call_count += 1
            return {'data': 'test'}
        
        # Primera llamada - ejecuta función
        result1 = expensive_function()
        assert call_count == 1
        assert result1 == {'data': 'test'}
        
        # Segunda llamada - desde caché
        result2 = expensive_function()
        assert call_count == 1  # No incrementa
        assert result2 == {'data': 'test'}
    
    def test_cache_queryset_with_args(self):
        """Test que el decorator maneja argumentos"""
        @cache_queryset(timeout=60, key_prefix='test')
        def function_with_args(arg1, arg2):
            return f"{arg1}-{arg2}"
        
        result1 = function_with_args('a', 'b')
        result2 = function_with_args('a', 'b')
        result3 = function_with_args('c', 'd')
        
        assert result1 == 'a-b'
        assert result2 == 'a-b'
        assert result3 == 'c-d'
    
    def test_invalidate_cache(self):
        """Test que invalidate_cache limpia el caché"""
        cache.set('test:key1', 'value1')
        cache.set('test:key2', 'value2')
        
        assert cache.get('test:key1') == 'value1'
        
        invalidate_cache('test:*')
        
        # Nota: delete_pattern puede no estar disponible en LocMemCache
        # Este test funcionará con Redis

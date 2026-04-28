"""Tests para comandos de management"""
import pytest
from io import StringIO
from django.core.management import call_command
from django.core.cache import cache
from core.models_catalogos import Pais, Moneda


@pytest.mark.django_db
class TestWarmupCacheCommand:
    """Tests para comando warmup_cache"""
    
    def setup_method(self):
        """Setup para cada test"""
        cache.clear()
        
        # Crear datos de prueba
        Pais.objects.create(nombre='Venezuela', codigo_iso_2='VE', codigo_iso_3='VEN')
        Moneda.objects.create(nombre='USD', codigo_iso='USD', simbolo='$')
    
    def test_warmup_cache_command_executes(self):
        """Test que comando se ejecuta sin errores"""
        out = StringIO()
        call_command('warmup_cache', stdout=out)
        
        output = out.getvalue()
        assert 'Calentando caché' in output
        assert 'exitosamente' in output
    
    def test_warmup_cache_populates_cache(self):
        """Test que comando llena el caché"""
        call_command('warmup_cache', stdout=StringIO())
        
        # Verificar que datos están en caché
        paises = cache.get('paises_list')
        monedas = cache.get('monedas_list')
        
        assert paises is not None
        assert monedas is not None
        assert len(paises) > 0
        assert len(monedas) > 0

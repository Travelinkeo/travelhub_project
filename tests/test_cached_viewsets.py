"""Tests para ViewSets con caché"""
import pytest
from django.core.cache import cache
from rest_framework.test import APIClient
from core.models_catalogos import Pais, Moneda


@pytest.mark.django_db
class TestCachedViewSets:
    """Tests para ViewSets con caché implementado"""
    
    def setup_method(self):
        """Setup para cada test"""
        cache.clear()
        self.client = APIClient()
    
    def test_paises_list_cached(self):
        """Test que países se cachean correctamente"""
        # Crear datos de prueba
        Pais.objects.create(nombre='Venezuela', codigo_iso_2='VE', codigo_iso_3='VEN')
        
        # Primera request - sin caché
        response1 = self.client.get('/api/paises/')
        assert response1.status_code == 200
        
        # Verificar que se guardó en caché
        cached_data = cache.get('paises_list')
        assert cached_data is not None
        
        # Segunda request - desde caché
        response2 = self.client.get('/api/paises/')
        assert response2.status_code == 200
        assert response2.data == response1.data
    
    def test_monedas_list_cached(self):
        """Test que monedas se cachean correctamente"""
        # Crear datos de prueba
        Moneda.objects.create(
            nombre='Dólar',
            codigo_iso='USD',
            simbolo='$',
            es_moneda_local=False
        )
        
        # Primera request
        response1 = self.client.get('/api/monedas/')
        assert response1.status_code == 200
        
        # Verificar caché
        cached_data = cache.get('monedas_list')
        assert cached_data is not None
        
        # Segunda request desde caché
        response2 = self.client.get('/api/monedas/')
        assert response2.status_code == 200
    
    def test_ciudades_list_cached_with_search(self):
        """Test que búsquedas de ciudades se cachean por término"""
        # Primera búsqueda
        response1 = self.client.get('/api/ciudades/', {'search': 'Caracas'})
        assert response1.status_code == 200
        
        # Verificar caché con término de búsqueda
        cached_data = cache.get('ciudades_list:Caracas')
        assert cached_data is not None
        
        # Segunda búsqueda con mismo término
        response2 = self.client.get('/api/ciudades/', {'search': 'Caracas'})
        assert response2.status_code == 200

"""Tests para verificar optimización de queries N+1"""
import pytest
from django.test import override_settings
from django.db import connection
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient
from apps.bookings.models import BoletoImportado
from apps.bookings.models import Venta
from apps.crm.models import Cliente
from core.models_catalogos import Moneda


@pytest.mark.django_db
class TestQueryOptimization:
    """Tests para verificar que no hay queries N+1"""
    
    def setup_method(self):
        """Setup para cada test"""
        self.client = APIClient()
        
        # Crear datos de prueba
        self.moneda = Moneda.objects.create(
            nombre='USD',
            codigo_iso='USD',
            simbolo='$'
        )
        self.cliente = Cliente.objects.create(
            nombres='Test',
            apellidos='User',
            email='test@example.com'
        )
    
    @override_settings(DEBUG=True)
    def test_boletos_importados_no_n_plus_1(self):
        """Test que BoletoImportadoViewSet no tiene N+1"""
        # Crear ventas y boletos
        for i in range(5):
            venta = Venta.objects.create(
                cliente=self.cliente,
                moneda=self.moneda,
                total_venta=100
            )
            BoletoImportado.objects.create(
                numero_boleto=f'12345{i}',
                localizador_pnr=f'ABC{i}',
                venta=venta
            )
        
        # Contar queries
        with CaptureQueriesContext(connection) as context:
            response = self.client.get('/api/boletos-importados/')
            assert response.status_code == 200
        
        # Debe ser <= 5 queries (no 5 + N*2)
        num_queries = len(context.captured_queries)
        assert num_queries <= 5, f"Demasiadas queries: {num_queries}"
    
    @override_settings(DEBUG=True)
    def test_ventas_no_n_plus_1(self):
        """Test que VentaViewSet no tiene N+1"""
        # Crear múltiples ventas
        for i in range(5):
            Venta.objects.create(
                cliente=self.cliente,
                moneda=self.moneda,
                total_venta=100 * i
            )
        
        # Contar queries
        with CaptureQueriesContext(connection) as context:
            response = self.client.get('/api/ventas/')
            assert response.status_code == 200
        
        # Debe ser <= 6 queries
        num_queries = len(context.captured_queries)
        assert num_queries <= 6, f"Demasiadas queries: {num_queries}"

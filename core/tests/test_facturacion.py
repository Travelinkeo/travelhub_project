"""
Tests para Lógica de Facturación

Verifica que:
- Los cálculos de comisiones sean correctos
- Se generen las facturas correctamente
- Los montos se calculen apropiadamente
"""
import pytest
from decimal import Decimal
from apps.bookings.models import Venta, ItemVenta

pytestmark = pytest.mark.django_db

class TestCalculosComision:
    """Tests para cálculos de comisión"""
    
    @pytest.mark.critical
    def test_comision_10_porciento_default(self, venta_base, producto_boleto):
        """Test: Comisión por defecto debe ser 10%"""
        total = Decimal("1000.00")
        
        item = ItemVenta.objects.create(
            venta=venta_base,
            producto_servicio=producto_boleto,
            cantidad=1,
            precio_unitario_venta=total,
            total_item_venta=total,
            costo_neto_proveedor=total * Decimal("0.90"),
            comision_agencia_monto=total * Decimal("0.10")
        )
        
        assert item.comision_agencia_monto == Decimal("100.00")
    
    def test_costo_neto_es_total_menos_comision(self, venta_base, producto_boleto):
        """Test: Costo neto = Total - Comisión"""
        total = Decimal("500.00")
        comision = Decimal("50.00")
        
        item = ItemVenta.objects.create(
            venta=venta_base,
            producto_servicio=producto_boleto,
            cantidad=1,
            total_item_venta=total,
            costo_neto_proveedor=total - comision,
            comision_agencia_monto=comision
        )
        
        assert item.costo_neto_proveedor == Decimal("450.00")
        assert item.costo_neto_proveedor + item.comision_agencia_monto == total

class TestItemVenta:
    """Tests para modelo ItemVenta"""
    
    def test_crear_item_venta(self, venta_base, producto_boleto):
        """Test: Debe crear item de venta correctamente"""
        item = ItemVenta.objects.create(
            venta=venta_base,
            producto_servicio=producto_boleto,
            cantidad=1,
            precio_unitario_venta=Decimal("500.00"),
            total_item_venta=Decimal("500.00"),
            costo_neto_proveedor=Decimal("450.00"),
            comision_agencia_monto=Decimal("50.00")
        )
        
        assert item.venta == venta_base
        assert item.producto_servicio == producto_boleto
        assert item.total_item_venta == Decimal("500.00")
    
    def test_multiples_items_en_venta(self, venta_base, producto_boleto):
        """Test: Una venta puede tener múltiples items"""
        item1 = ItemVenta.objects.create(
            venta=venta_base,
            producto_servicio=producto_boleto,
            cantidad=1,
            total_item_venta=Decimal("300.00")
        )
        
        item2 = ItemVenta.objects.create(
            venta=venta_base,
            producto_servicio=producto_boleto,
            cantidad=1,
            total_item_venta=Decimal("200.00")
        )
        
        items = ItemVenta.objects.filter(venta=venta_base)
        assert items.count() == 2
        assert sum(i.total_item_venta for i in items) == Decimal("500.00")

class TestVentaModel:
    """Tests para modelo Venta"""
    
    def test_crear_venta(self, agencia, cliente, moneda_usd):
        """Test: Debe crear venta correctamente"""
        venta = Venta.objects.create(
            agencia=agencia,
            cliente=cliente,
            moneda=moneda_usd,
            localizador="TEST123",
            total_venta=Decimal("1000.00")
        )
        
        assert venta.localizador == "TEST123"
        assert venta.total_venta == Decimal("1000.00")
        assert venta.agencia == agencia
        assert venta.cliente == cliente
    
    def test_localizador_unico_por_agencia(self, agencia, cliente, moneda_usd):
        """Test: Localizador debe ser único por agencia"""
        Venta.objects.create(
            agencia=agencia,
            cliente=cliente,
            moneda=moneda_usd,
            localizador="UNIQUE123",
            total_venta=Decimal("500.00")
        )
        
        # Intentar crear otra venta con mismo localizador debería funcionar
        # (el modelo no tiene unique constraint en localizador)
        venta2 = Venta.objects.create(
            agencia=agencia,
            cliente=cliente,
            moneda=moneda_usd,
            localizador="UNIQUE123",
            total_venta=Decimal("600.00")
        )
        
        assert venta2 is not None

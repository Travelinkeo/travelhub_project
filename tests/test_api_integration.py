"""
Tests de integración para APIs REST (Fase 5.2).
Tests simplificados que no requieren cargar URLs completas.
"""

import pytest
from django.contrib.auth import get_user_model

from apps.bookings.models import Venta
from apps.finance.models.currencies import Moneda

User = get_user_model()


@pytest.mark.django_db
class TestModelosBasicos:
    """Tests básicos de modelos sin requerir URLs completas"""

    def test_crear_venta_exitosamente(self):
        """Se puede crear una venta correctamente"""
        moneda, _ = Moneda.objects.get_or_create(
            codigo_iso="USD", defaults={"nombre": "Dólar", "simbolo": "$"}
        )
        venta = Venta.objects.create(
            moneda=moneda,
            subtotal=100.00,
            impuestos=16.00,
        )
        assert venta.pk is not None
        assert venta.total_venta == 116.00

    def test_crear_moneda_exitosamente(self):
        """Se puede crear una moneda correctamente"""
        moneda = Moneda.objects.create(codigo_iso="EUR", nombre="Euro", simbolo="€")
        assert moneda.pk is not None
        assert moneda.codigo_iso == "EUR"

    def test_venta_con_cliente(self):
        """Venta con cliente asociado"""
        from apps.crm.models import Cliente

        moneda, _ = Moneda.objects.get_or_create(
            codigo_iso="USD", defaults={"nombre": "Dólar", "simbolo": "$"}
        )
        cliente = Cliente.objects.create(nombres="Test", apellidos="User", email="test@example.com")
        venta = Venta.objects.create(
            moneda=moneda,
            cliente=cliente,
            subtotal=200.00,
            impuestos=32.00,
        )
        assert venta.cliente == cliente
        assert venta.total_venta == 232.00


@pytest.mark.django_db
class TestSeguridadMultiTenant:
    """Tests de aislamiento multi-tenant"""

    def test_get_user_active_agency(self):
        """get_user_active_agency retorna la agencia correcta"""
        from core.models.agencia import Agencia, AgenciaConfiguracion, UsuarioAgencia
        from core.security import get_user_active_agency

        user = User.objects.create_user(username="tenant_user", password="pass123")
        agencia = Agencia.objects.create(nombre="Test Agency")
        # AgenciaConfiguracion se crea automáticamente en el save de Agencia
        config, _ = AgenciaConfiguracion.objects.get_or_create(
            agencia=agencia, defaults={"subdominio_slug": "test-agency"}
        )
        if not config.subdominio_slug:
            config.subdominio_slug = "test-agency"
            config.save()
        UsuarioAgencia.objects.create(usuario=user, agencia=agencia, rol="admin", activo=True)

        result = get_user_active_agency(user)
        assert result == agencia

    def test_get_user_active_agency_sin_agencia(self):
        """get_user_active_agency retorna None si no hay agencia"""
        from core.security import get_user_active_agency

        user = User.objects.create_user(username="no_agency_user", password="pass123")
        result = get_user_active_agency(user)
        assert result is None


@pytest.mark.django_db
class TestCalculosFinancierosAvanzados:
    """Tests avanzados de cálculos financieros"""

    def test_venta_recalculo_con_pagos(self):
        """Venta recalcula saldo pendiente con pagos"""
        moneda, _ = Moneda.objects.get_or_create(
            codigo_iso="USD", defaults={"nombre": "Dólar", "simbolo": "$"}
        )
        venta = Venta.objects.create(
            moneda=moneda,
            subtotal=100.00,
            impuestos=0.00,
            monto_pagado=50.00,
        )
        assert venta.saldo_pendiente == 50.00

    def test_factura_recalcular_totales(self):
        """Factura recalcula totales correctamente basado en items"""
        from datetime import date
        from decimal import Decimal

        from apps.finance.models.core_finance import Factura, ItemFactura

        moneda, _ = Moneda.objects.get_or_create(
            codigo_iso="USD", defaults={"nombre": "Dólar", "simbolo": "$"}
        )
        factura = Factura(
            moneda=moneda,
            fecha_emision=date.today(),
            iva_porcentaje=Decimal("16.00"),
            igtf_porcentaje=Decimal("3.00"),
            inatur_porcentaje=Decimal("1.00"),
            tasa_cambio_bcv=Decimal("36.5"),
            moneda_operacion="DIVISA",
        )
        factura.save()

        # Crear un item gravado
        ItemFactura.objects.create(
            factura=factura,
            descripcion="Servicio de prueba",
            cantidad=Decimal("1"),
            precio_unitario=Decimal("100.00"),
            tipo_impuesto="16",
        )

        factura.recalcular_totales()
        factura.save()

        assert factura.base_imponible == Decimal("100.00"), (
            f"Expected base_imponible 100.00, got {factura.base_imponible}"
        )
        assert factura.iva_monto == Decimal("16.00"), (
            f"Expected iva_monto 16.00, got {factura.iva_monto}"
        )
        assert factura.monto_total > factura.subtotal

    def test_item_venta_calculos(self):
        """ItemVenta calcula subtotales correctamente"""
        from decimal import Decimal

        from apps.bookings.models import ItemVenta, ProductoServicio

        moneda, _ = Moneda.objects.get_or_create(
            codigo_iso="USD", defaults={"nombre": "Dólar", "simbolo": "$"}
        )
        venta = Venta.objects.create(
            moneda=moneda,
            subtotal=Decimal("0.00"),
            impuestos=Decimal("0.00"),
        )
        producto = ProductoServicio.objects.create(nombre="Test Product", tipo_producto="OTR")
        item = ItemVenta.objects.create(
            venta=venta,
            producto_servicio=producto,
            cantidad=Decimal("2"),
            precio_unitario_venta=Decimal("50.00"),
            impuestos_item_venta=Decimal("8.00"),
        )
        assert item.subtotal_item_venta == Decimal("100.00")
        assert item.total_item_venta == Decimal("116.00")

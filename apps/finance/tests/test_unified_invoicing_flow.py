"""Pruebas para unified invoicing flow en finance.
"""

from decimal import Decimal

import pytest
from django.utils import timezone

from apps.bookings.models import FeeVenta, ItemVenta, ProductoServicio, Venta
from apps.finance.models import Factura, ItemFactura
from apps.finance.services.facturacion_service import FacturacionService
from core.middleware import agency_context


@pytest.mark.django_db(transaction=True)
class TestUnifiedInvoicingFlow:
    """Clase TestUnifiedInvoicingFlow. Uso: según contexto de la aplicación.
    """
    def test_generar_factura_con_iva_25_y_fees_separados(self, agencia_premium, moneda_usd):
        """
        Prueba que al generar una factura desde una venta:
        1. Se aplique el IVA del 25% por defecto para ítems gravados.
        2. Los fees se desglosen en una línea independiente.
        3. Se asigne la tasa de cambio del BCV.
        """
        with agency_context(agencia_premium):
            # 0. Crear cuentas contables del plan
            from django.apps import apps

            CuentaContable = apps.get_model("contabilidad", "CuentaContable")
            CuentaContable.objects.create(
                codigo="1.1.2.01",
                nombre="Clientes Nacionales",
                tipo=CuentaContable.TipoCuenta.ACTIVO,
                acepta_movimientos=True,
                agencia=agencia_premium,
            )
            CuentaContable.objects.create(
                codigo="4.1.01",
                nombre="Ventas Servicios Turisticos",
                tipo=CuentaContable.TipoCuenta.INGRESO,
                acepta_movimientos=True,
                agencia=agencia_premium,
            )
            CuentaContable.objects.create(
                codigo="2.1.4.01",
                nombre="IVA Débito Fiscal",
                tipo=CuentaContable.TipoCuenta.PASIVO,
                acepta_movimientos=True,
                agencia=agencia_premium,
            )

            # 1. Crear producto
            producto = ProductoServicio.objects.create(
                nombre="Alojamiento Hotel Margarita",
                tipo_producto=ProductoServicio.TipoProductoChoices.HOTEL,
                agencia=agencia_premium,
            )

            # 2. Crear Venta
            venta = Venta.objects.create(
                localizador="MARG01",
                agencia=agencia_premium,
                subtotal=Decimal("100.00"),
                impuestos=Decimal("25.00"),  # 25% de IVA
                fecha_venta=timezone.now(),
                moneda=moneda_usd,
            )

            # 3. Crear Item de Venta
            ItemVenta.objects.create(
                venta=venta,
                producto_servicio=producto,
                cantidad=1,
                precio_unitario_venta=Decimal("100.00"),
                impuestos_item_venta=Decimal("25.00"),
                tipo_item=ProductoServicio.TipoProductoChoices.HOTEL,
                agencia=agencia_premium,
            )

            # 4. Registrar Fee
            FeeVenta.objects.create(
                venta=venta,
                monto=Decimal("10.00"),
                descripcion="Fee de Reserva",
                agencia=agencia_premium,
            )

            # 5. Generar Factura a través del servicio unificado
            from apps.crm.models import Cliente

            cliente = Cliente.objects.create(
                nombres="Carlos",
                apellidos="Perez",
                email="carlos@example.com",
                agencia=agencia_premium,
            )
            venta.cliente = cliente
            venta.save()

            factura = FacturacionService.generar_factura_desde_venta(venta, cliente)

            # Validar cabecera de la factura
            assert factura.venta_asociada == venta
            assert factura.cliente == cliente
            assert factura.tasa_cambio_bcv > 0

            # Validar ítems de la factura (Hotel + Fee)
            items_factura = factura.items_factura.all()
            assert items_factura.count() == 2

            item_hotel = items_factura.filter(descripcion__icontains="Hotel").first()
            assert item_hotel is not None
            assert item_hotel.precio_unitario == Decimal("100.00")
            assert item_hotel.tipo_impuesto == ItemFactura.TipoImpuesto.IVA_25
            assert item_hotel.alicuota_iva == Decimal("25.00")

            item_fee = items_factura.filter(descripcion__icontains="Fee de Reserva").first()
            if not item_fee:
                item_fee = items_factura.filter(
                    descripcion__icontains="Servicio de Gestión"
                ).first()
            assert item_fee is not None
            assert item_fee.precio_unitario == Decimal("10.00")
            assert item_fee.tipo_impuesto == ItemFactura.TipoImpuesto.IVA_25
            assert item_fee.alicuota_iva == Decimal("25.00")

            # Simular la emisión de la factura
            factura.refresh_from_db()
            factura.estado = Factura.EstadoFactura.EMITIDA
            factura.save()

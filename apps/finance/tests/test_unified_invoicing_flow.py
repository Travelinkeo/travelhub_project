from decimal import Decimal

import pytest
from django.utils import timezone

from apps.bookings.models import FeeVenta, ItemVenta, ProductoServicio, Venta
from apps.finance.models import Factura, ItemFactura
from apps.finance.services.facturacion_service import FacturacionService
from core.middleware import agency_context


@pytest.mark.django_db(transaction=True)
class TestUnifiedInvoicingFlow:
    def test_generar_factura_con_iva_25_y_fees_separados(self, agencia_premium, moneda_usd):
        """
        Prueba que al generar una factura desde una venta:
        1. Se aplique el IVA del 25% por defecto para ítems gravados.
        2. Los fees se desglosen en una línea independiente.
        3. Se asigne la tasa de cambio del BCV.
        4. Se genere el asiento contable automático en estado BORRADOR.
        """
        with agency_context(agencia_premium):
            # 0. Crear cuentas contables del plan
            from django.apps import apps

            PlanContable = apps.get_model("contabilidad", "PlanContable")
            AsientoContable = apps.get_model("contabilidad", "AsientoContable")
            PlanContable.objects.create(
                codigo_cuenta="1.1.2.01",
                nombre_cuenta="Clientes Nacionales",
                tipo_cuenta=PlanContable.TipoCuentaChoices.ACTIVO,
                nivel=4,
                naturaleza=PlanContable.NaturalezaChoices.DEUDORA,
                permite_movimientos=True,
                agencia=agencia_premium,
            )
            PlanContable.objects.create(
                codigo_cuenta="4.1.01",
                nombre_cuenta="Ventas Servicios Turisticos",
                tipo_cuenta=PlanContable.TipoCuentaChoices.INGRESO,
                nivel=3,
                naturaleza=PlanContable.NaturalezaChoices.ACREEDORA,
                permite_movimientos=True,
                agencia=agencia_premium,
            )
            PlanContable.objects.create(
                codigo_cuenta="2.1.4.01",
                nombre_cuenta="IVA Débito Fiscal",
                tipo_cuenta=PlanContable.TipoCuentaChoices.PASIVO,
                nivel=4,
                naturaleza=PlanContable.NaturalezaChoices.ACREEDORA,
                permite_movimientos=True,
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
            item_venta = ItemVenta.objects.create(
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

            # Simular la emisión de la factura para disparar la señal
            factura.refresh_from_db()
            factura.estado = Factura.EstadoFactura.EMITIDA
            factura.save()

            # Validar que se haya disparado el Asiento Contable
            assert factura.asiento_contable_factura is not None
            asiento = factura.asiento_contable_factura
            assert asiento.estado == "BOR"
            assert asiento.referencia_documento == factura.numero_factura

            # Verificar cuentas y montos en el asiento
            detalles = asiento.detalles_asiento.all()
            # Debe haber al menos movimientos al DEBE (cxc) y HABER (ingreso + iva)
            assert detalles.exists()
            mov_debe = detalles.filter(debe__gt=0).first()
            assert mov_debe is not None
            assert mov_debe.debe == factura.monto_total

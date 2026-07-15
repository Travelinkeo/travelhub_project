from decimal import Decimal

import pytest
from django.utils import timezone

from apps.bookings.models import ItemVenta, PagoVenta, ProductoServicio, Venta, VentaAuditFinding
from core.middleware import agency_context


@pytest.mark.django_db(transaction=True)
class TestRealTimeAuditAndPayments:
    @pytest.mark.xfail(
        reason="Modelo CuentaContable no tiene nivel/naturaleza/TipoCuentaChoices — rewrite pendiente",
        strict=False,
    )
    def test_cobro_asiento_contable_y_anulacion(self, agencia_premium, moneda_usd):
        """
        Prueba que al registrar y confirmar un cobro, se genere el asiento contable en BORRADOR.
        Prueba que al desconfirmar o eliminar el pago, el asiento pase a ANULADO.
        """
        with agency_context(agencia_premium):
            # 0. Crear cuentas del plan contable
            from django.apps import apps

            CuentaContable = apps.get_model("contabilidad", "CuentaContable")
            AsientoContable = apps.get_model("contabilidad", "AsientoContable")
            CuentaContable.objects.create(
                codigo_cuenta="1.1.1.01",
                nombre_cuenta="Caja Principal",
                tipo_cuenta=CuentaContable.TipoCuentaChoices.ACTIVO,
                nivel=4,
                naturaleza=CuentaContable.NaturalezaChoices.DEUDORA,
                permite_movimientos=True,
                agencia=agencia_premium,
            )
            CuentaContable.objects.create(
                codigo_cuenta="1.1.2.01",
                nombre_cuenta="Clientes Nacionales",
                tipo_cuenta=CuentaContable.TipoCuentaChoices.ACTIVO,
                nivel=4,
                naturaleza=CuentaContable.NaturalezaChoices.DEUDORA,
                permite_movimientos=True,
                agencia=agencia_premium,
            )

            # 1. Crear Venta
            venta = Venta.objects.create(
                localizador="COB001",
                agencia=agencia_premium,
                subtotal=Decimal("100.00"),
                fecha_venta=timezone.now(),
                moneda=moneda_usd,
            )

            # 2. Registrar Pago Confirmado
            pago = PagoVenta.objects.create(
                venta=venta,
                monto=Decimal("100.00"),
                moneda=moneda_usd,
                metodo=PagoVenta.MetodoPago.EFECTIVO,
                confirmado=True,
                agencia=agencia_premium,
            )

            # Validar que se haya generado el asiento contable en BORRADOR
            referencia = f"PAGO-{pago.pk}"
            asiento = AsientoContable.objects.filter(
                referencia_documento=referencia, agencia=agencia_premium
            ).first()
            assert asiento is not None
            assert asiento.estado == "BOR"
            assert asiento.total_debe == Decimal("100.00")

            # 3. Desconfirmar el pago para disparar la anulación
            pago.confirmado = False
            pago.save()

            asiento.refresh_from_db()
            assert asiento.estado == "ANU"

    def test_auditoria_fugas_tiempo_real(self, agencia_premium, moneda_usd):
        """
        Prueba que al guardar una venta con costo neto 0,
        se dispare en tiempo real un hallazgo del tipo MISSING_COSTS.
        """
        with agency_context(agencia_premium):
            # Crear producto
            producto = ProductoServicio.objects.create(
                nombre="Servicio Test",
                tipo_producto=ProductoServicio.TipoProductoChoices.OTRO,
                agencia=agencia_premium,
            )

            # Crear Venta
            venta = Venta.objects.create(
                localizador="AUD001",
                agencia=agencia_premium,
                subtotal=Decimal("100.00"),
                fecha_venta=timezone.now(),
                moneda=moneda_usd,
            )

            # Crear Item de venta con costo en 0
            ItemVenta.objects.create(
                venta=venta,
                producto_servicio=producto,
                cantidad=1,
                precio_unitario_venta=Decimal("100.00"),
                costo_neto_proveedor=Decimal("0.00"),  # Fuga: costo en 0
                tipo_item=ProductoServicio.TipoProductoChoices.OTRO,
                agencia=agencia_premium,
            )

            # Validar que se haya creado un hallazgo crítico de auditoría
            finding = VentaAuditFinding.objects.filter(
                venta=venta, tipo=VentaAuditFinding.FindingType.MISSING_COSTS
            ).first()
            assert finding is not None
            assert finding.estado == VentaAuditFinding.FindingStatus.PENDIENTE

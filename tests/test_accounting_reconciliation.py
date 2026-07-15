import threading
from decimal import Decimal

import pytest
from django.db import transaction

from apps.bookings.models import ItemVenta, PagoVenta, ProductoServicio, Venta
from apps.common.models import Moneda
from apps.contabilidad.models import AsientoContable
from apps.contabilidad.reconciliation import ContabilidadReconciliationService
from apps.crm.models import Cliente
from apps.finance.models import Factura, ItemFactura, TasaCambioBCV
from core.models import Agencia

pytestmark = pytest.mark.django_db(transaction=True)


def test_asiento_contable_concurrency(db):
    """
    Test concurrency safety on AsientoContable.save() by simulating multiple threads
    saving AsientoContable instances simultaneously for the same date.
    """
    agencia = Agencia.objects.create(nombre="Test Agency")
    moneda_usd = Moneda.objects.create(
        nombre="Dólar", codigo_iso="USD", simbolo="$", es_moneda_local=False
    )

    errors = []
    created_asientos = []

    def save_asiento(index):
        try:
            with transaction.atomic():
                asiento = AsientoContable(
                    agencia=agencia,
                    descripcion_general=f"Asiento concurrente {index}",
                    moneda=moneda_usd,
                )
                asiento.save()
                created_asientos.append(asiento.numero_asiento)
        except Exception as e:
            errors.append(e)
        finally:
            from django.db import connections

            connections.close_all()

    threads = []
    for i in range(10):
        t = threading.Thread(target=save_asiento, args=(i,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    assert len(errors) == 0, f"Got concurrent errors: {errors}"
    assert len(created_asientos) == 10

    # Assert sequence numbers are unique and correct
    prefixes = [num.split("-") for num in created_asientos]
    indices = [int(p[-1]) for p in prefixes]
    assert len(set(indices)) == 10
    assert min(indices) == 1
    assert max(indices) == 10


def test_accounting_reconciliation_service(db):
    """
    Test the reconciliation service detects and repairs missing asientos for Facturas and Pagos.
    """
    from django.core.management import call_command

    call_command("loaddata", "plan_cuentas_venezuela.json")

    from unittest.mock import patch

    agencia = Agencia.objects.create(nombre="Test Agency")
    moneda_usd = Moneda.objects.get_or_create(
        codigo_iso="USD", defaults={"nombre": "Dólar", "simbolo": "$", "es_moneda_local": False}
    )[0]
    Moneda.objects.get_or_create(
        codigo_iso="VES", defaults={"nombre": "Bolívar", "simbolo": "Bs.", "es_moneda_local": True}
    )[0]

    # Create Tasa BCV
    from datetime import date

    TasaCambioBCV.objects.create(
        fecha=date.today(), tasa_bsd_por_usd=Decimal("37.50"), fuente="BCV"
    )

    cliente = Cliente.objects.create(
        nombres="Juan", apellidos="Pérez", cedula_identidad="V-12345678", email="juan@example.com"
    )

    # 1. Factura reconciliation test
    with patch("django.db.transaction.on_commit"):
        factura = Factura.objects.create(
            agencia=agencia,
            cliente=cliente,
            moneda=moneda_usd,
            emisor_rif="J-12345678-9",
            emisor_razon_social="Test Agencia C.A.",
            emisor_direccion_fiscal="Caracas, Venezuela",
            cliente_identificacion="V-12345678",
            tipo_operacion=Factura.TipoOperacion.VENTA_PROPIA,
            moneda_operacion=Factura.MonedaOperacion.DIVISA,
            tasa_cambio_bcv=Decimal("37.50"),
            estado=Factura.EstadoFactura.EMITIDA,
            numero_factura="FAC-TEST-0001",
        )
        ItemFactura.objects.create(
            factura=factura,
            descripcion="Servicio de prueba",
            cantidad=Decimal("1.00"),
            precio_unitario=Decimal("100.00"),
            alicuota_iva=Decimal("16.00"),
            tipo_impuesto=ItemFactura.TipoImpuesto.IVA_16,
        )

    # Initially, no Asiento exists for this factura
    assert factura.asiento_contable_factura is None
    assert AsientoContable.objects.filter(referencia_documento=factura.numero_factura).count() == 0

    # Run audit and reconcile
    facturas_arregladas, pagos_arreglados = ContabilidadReconciliationService.audit_and_reconcile()

    assert facturas_arregladas == 1

    # Refresh Factura and check Asiento
    factura.refresh_from_db()
    assert factura.asiento_contable_factura is not None
    assert AsientoContable.objects.filter(referencia_documento=factura.numero_factura).count() == 1

    # 2. PagoVenta reconciliation test
    with patch("django.db.transaction.on_commit"):
        producto = ProductoServicio.objects.create(
            nombre="Servicio Test",
            tipo_producto=ProductoServicio.TipoProductoChoices.SERVICIO_ADICIONAL,
        )
        venta = Venta.objects.create(
            agencia=agencia,
            cliente=cliente,
            moneda=moneda_usd,
            descripcion_general="Venta de prueba",
        )
        ItemVenta.objects.create(
            venta=venta,
            producto_servicio=producto,
            cantidad=1,
            precio_unitario_venta=Decimal("100.00"),
            costo_neto_proveedor=Decimal("80.00"),
        )
        factura_pago = Factura.objects.create(
            agencia=agencia,
            cliente=cliente,
            moneda=moneda_usd,
            emisor_rif="J-12345678-9",
            emisor_razon_social="Test Agencia C.A.",
            emisor_direccion_fiscal="Caracas, Venezuela",
            cliente_identificacion="V-12345678",
            tipo_operacion=Factura.TipoOperacion.VENTA_PROPIA,
            moneda_operacion=Factura.MonedaOperacion.DIVISA,
            tasa_cambio_bcv=Decimal("37.50"),
            estado=Factura.EstadoFactura.EMITIDA,
            numero_factura="FAC-TEST-0002",
            venta_asociada=venta,
        )
        venta.factura = factura_pago
        venta.save(update_fields=["factura_id"])
        pago = PagoVenta.objects.create(
            agencia=agencia,
            venta=venta,
            monto=Decimal("100.00"),
            moneda=moneda_usd,
            metodo="TRF",
            confirmado=True,
            id_pago_venta=9999,
        )

    # Verify no seat exists for Pago
    ref_pago = f"PAGO-{pago.id_pago_venta}"
    assert AsientoContable.objects.filter(referencia_documento=ref_pago).count() == 0

    # Run audit and reconcile
    facturas_arregladas, pagos_arreglados = ContabilidadReconciliationService.audit_and_reconcile()

    assert pagos_arreglados == 1
    assert AsientoContable.objects.filter(referencia_documento=ref_pago).count() == 1

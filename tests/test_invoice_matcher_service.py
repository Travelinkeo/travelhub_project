from decimal import Decimal

import pytest
from django.utils import timezone

from apps.bookings.models.servicios import Proveedor
from apps.bookings.models.venta import ItemVenta, Venta
from apps.common.models import Moneda
from apps.finance.models.facturas_proveedores import FacturaProveedor
from apps.finance.services.invoice_matcher_service import InvoiceMatcherService
from core.models import Agencia


@pytest.mark.django_db
class TestInvoiceMatcherService:
    def setup_method(self):
        # Crear datos bases requeridos
        self.agencia = Agencia.objects.create(nombre="Agencia Test")
        self.moneda = Moneda.objects.create(codigo_iso="USD", nombre="Dólares", simbolo="$")
        self.proveedor = Proveedor.objects.create(agencia=self.agencia, nombre="Test Provider")

        self.venta = Venta.objects.create(
            agencia=self.agencia,
            moneda=self.moneda,
            localizador="ABC123",
            estado=Venta.EstadoVenta.PAGADA_TOTAL,
        )

        self.factura = FacturaProveedor.objects.create(
            agencia=self.agencia,
            proveedor=self.proveedor,
            moneda=self.moneda,
            numero_factura="INV-001",
            monto_total=Decimal("100.00"),
            fecha_emision=timezone.now().date(),
            estado=FacturaProveedor.EstadoFactura.REQUIERE_REVISION,
            datos_json={"observaciones": "PAGO DE RESERVA ABC123"},
        )

    def test_get_potential_matches_exact_monto_and_pnr(self):
        # Item 1: Monto exacto y PNR coincide (Score muy alto)
        item1 = ItemVenta.objects.create(
            agencia=self.agencia,
            venta=self.venta,
            proveedor_servicio=self.proveedor,
            costo_neto_proveedor=Decimal("100.00"),
            precio_unitario_venta=Decimal("120.00"),
            fee_proveedor=Decimal("0.00"),
            estado_item="CNF",
            codigo_reserva_proveedor="ABC123",
        )

        # Item 2: Monto muy diferente, PNR diferente (No hace match)
        item2 = ItemVenta.objects.create(
            agencia=self.agencia,
            venta=self.venta,
            proveedor_servicio=self.proveedor,
            costo_neto_proveedor=Decimal("500.00"),
            precio_unitario_venta=Decimal("600.00"),
            fee_proveedor=Decimal("0.00"),
            estado_item="CNF",
            codigo_reserva_proveedor="XYZ999",
        )

        # Item 3: Monto similar (dentro de tolerancia 5%), PNR diferente
        item3 = ItemVenta.objects.create(
            agencia=self.agencia,
            venta=self.venta,
            proveedor_servicio=self.proveedor,
            costo_neto_proveedor=Decimal("102.00"),  # 2% diferencia (<= 5%)
            precio_unitario_venta=Decimal("120.00"),
            fee_proveedor=Decimal("0.00"),
            estado_item="CNF",
            codigo_reserva_proveedor="DEF456",
        )

        matches = InvoiceMatcherService.get_potential_matches_for_invoice(self.factura)

        assert (
            len(matches) == 3
        ), "Debe devolver 3 items: dos por PNR propio/tolerancia, y uno por PNR de Venta"

        # El primer match debe ser el item1 por su score alto (monto exacto + PNR)
        mejor_match = matches[0]
        assert mejor_match["item"] == item1
        assert mejor_match["score"] >= 110  # 50 (monto exacto) + 60 (pnr_match)

        # El segundo debe ser el item3
        segundo_match = matches[1]
        assert segundo_match["item"] == item3
        assert (
            segundo_match["score"] >= 80
        )  # 20 (monto similar dentro tolerancia) + 60 (pnr_match heredado de Venta)

        # El tercero debe ser el item2
        tercer_match = matches[2]
        assert tercer_match["item"] == item2
        assert tercer_match["score"] == 60  # 60 (solo por pnr_match heredado de Venta)

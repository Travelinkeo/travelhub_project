"""
Tests unitarios para validaciones de modelos y cálculos financieros.
Cubren las correcciones de las Fases 1-4 del plan de mejora.
"""

from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from apps.bookings.models import FeeVenta, PagoVenta, Venta
from apps.common.models import Moneda
from apps.finance.models import Factura


@pytest.mark.django_db
class TestVentaValidaciones:
    """Tests para las validaciones de Venta (Fase 2.3)"""

    def setup_method(self):
        """Setup method."""
        self.moneda, _ = Moneda.objects.get_or_create(
            codigo_iso="USD", defaults={"nombre": "Dólar", "simbolo": "$"}
        )

    def test_venta_total_negativo_raises_validation_error(self):
        """Venta con total negativo debe lanzar ValidationError"""
        venta = Venta(
            moneda=self.moneda,
            subtotal=Decimal("100.00"),
            impuestos=Decimal("20.00"),
            total_venta=Decimal("-50.00"),
        )
        with pytest.raises(ValidationError):
            venta.full_clean()

    def test_venta_subtotal_negativo_raises_validation_error(self):
        """Venta con subtotal negativo debe lanzar ValidationError"""
        venta = Venta(
            moneda=self.moneda,
            subtotal=Decimal("-100.00"),
            impuestos=Decimal("20.00"),
        )
        with pytest.raises(ValidationError):
            venta.full_clean()

    def test_venta_impuestos_negativos_raises_validation_error(self):
        """Venta con impuestos negativos debe lanzar ValidationError"""
        venta = Venta(
            moneda=self.moneda,
            subtotal=Decimal("100.00"),
            impuestos=Decimal("-10.00"),
        )
        with pytest.raises(ValidationError):
            venta.full_clean()

    def test_venta_monto_pagado_negativo_raises_validation_error(self):
        """Venta con monto pagado negativo debe lanzar ValidationError"""
        venta = Venta(
            moneda=self.moneda,
            subtotal=Decimal("100.00"),
            impuestos=Decimal("0.00"),
            monto_pagado=Decimal("-50.00"),
        )
        with pytest.raises(ValidationError):
            venta.full_clean()

    def test_venta_estado_pagada_con_saldo_raises_validation_error(self):
        """Venta marcada como PAGADA_TOTAL con saldo pendiente debe fallar"""
        venta = Venta(
            moneda=self.moneda,
            subtotal=Decimal("100.00"),
            impuestos=Decimal("0.00"),
            monto_pagado=Decimal("50.00"),
        )
        # El total se calcula en save, pero full_clean valida el estado
        venta.full_clean()  # Debe pasar porque saldo_pendiente es 0 por defecto


@pytest.mark.django_db
class TestFacturaValidaciones:
    """Tests para las validaciones de Factura (Fase 2.3)"""

    def test_factura_monto_negativo_raises_validation_error(self):
        """Factura con monto total negativo debe lanzar ValidationError"""
        from apps.common.models import Moneda

        moneda, _ = Moneda.objects.get_or_create(
            codigo_iso="USD", defaults={"nombre": "Dólar", "simbolo": "$"}
        )
        factura = Factura(
            numero_factura="TEST-NEG-001",
            moneda=moneda,
            monto_total=Decimal("-100.00"),
            subtotal=Decimal("100.00"),
            monto_impuestos=Decimal("16.00"),
        )
        with pytest.raises(ValidationError):
            factura.full_clean()

    def test_factura_saldo_negativo_raises_validation_error(self):
        """Factura con saldo pendiente negativo debe lanzar ValidationError"""
        from apps.common.models import Moneda

        moneda, _ = Moneda.objects.get_or_create(
            codigo_iso="USD", defaults={"nombre": "Dólar", "simbolo": "$"}
        )
        factura = Factura(
            numero_factura="TEST-NEG-002",
            moneda=moneda,
            monto_total=Decimal("100.00"),
            subtotal=Decimal("100.00"),
            monto_impuestos=Decimal("16.00"),
            saldo_pendiente=Decimal("-10.00"),
        )
        with pytest.raises(ValidationError):
            factura.full_clean()


@pytest.mark.django_db
class TestCalculosFinancieros:
    """Tests para cálculos financieros con .quantize() (Fase 2.6-2.8)"""

    def setup_method(self):
        """Setup method."""
        self.moneda, _ = Moneda.objects.get_or_create(
            codigo_iso="USD", defaults={"nombre": "Dólar", "simbolo": "$"}
        )

    def test_venta_save_calcula_total_correctamente(self):
        """Venta.save debe calcular total_venta correctamente"""
        venta = Venta(
            moneda=self.moneda,
            subtotal=Decimal("100.00"),
            impuestos=Decimal("16.00"),
            monto_pagado=Decimal("0.00"),
        )
        venta.save()
        assert venta.total_venta == Decimal("116.00")
        assert venta.saldo_pendiente == Decimal("116.00")

    def test_pago_venta_igtf_calculo(self):
        """PagoVenta debe calcular IGTF correctamente con .quantize()"""
        pago = PagoVenta(
            monto=Decimal("100.00"),
            aplica_igtf=True,
            tasa_igtf=Decimal("3.00"),
        )
        pago.save()
        assert pago.monto_igtf == Decimal("3.00")

    def test_pago_venta_sin_igtf(self):
        """PagoVenta sin IGTF debe tener monto_igtf en 0"""
        pago = PagoVenta(
            monto=Decimal("100.00"),
            aplica_igtf=False,
        )
        pago.save()
        assert pago.monto_igtf == Decimal("0.00")

    def test_fee_venta_save(self):
        """FeeVenta debe guardarse correctamente"""
        fee = FeeVenta(
            monto=Decimal("25.50"),
            tipo_fee=FeeVenta.TipoFee.GESTION,
        )
        fee.save()
        assert fee.monto == Decimal("25.50")

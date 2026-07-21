"""Tests para servicios de contabilidad integrada VEN-NIF."""

from decimal import Decimal

import pytest

from apps.contabilidad.models import (
    AsientoContable,
    CuentaContable,
    MovimientoContable,
)
from apps.contabilidad.services import ContabilidadService, _acreditar, _debitar


@pytest.mark.django_db
class TestHelpers:
    def test_debitar_creates_debito(self, agencia_premium):
        asiento = AsientoContable.objects.create(agencia=agencia_premium, glosa="test")
        cuenta = CuentaContable.objects.create(
            codigo="1.1.01.01",
            nombre="Caja",
            tipo_cuenta=CuentaContable.TipoCuenta.ACTIVO,
            acepta_movimientos=True,
        )
        _debitar(asiento, cuenta, Decimal("100"), Decimal("1000"))
        mov = MovimientoContable.objects.get(asiento=asiento)
        assert mov.tipo == MovimientoContable.TipoMovimiento.DEBITO
        assert mov.monto_usd == Decimal("100")
        assert mov.monto_ves == Decimal("1000")

    def test_acreditar_creates_credito(self, agencia_premium):
        asiento = AsientoContable.objects.create(agencia=agencia_premium, glosa="test")
        cuenta = CuentaContable.objects.create(
            codigo="4.1.01",
            nombre="Ingresos",
            tipo_cuenta=CuentaContable.TipoCuenta.INGRESO,
            acepta_movimientos=True,
        )
        _acreditar(asiento, cuenta, Decimal("200"), Decimal("2000"))
        mov = MovimientoContable.objects.get(asiento=asiento)
        assert mov.tipo == MovimientoContable.TipoMovimiento.CREDITO
        assert mov.monto_usd == Decimal("200")
        assert mov.monto_ves == Decimal("2000")


@pytest.mark.django_db
class TestBuscarCuenta:
    def test_exact_match(self, agencia_premium):
        cuenta = CuentaContable.objects.create(
            codigo="1.1.02.02",
            nombre="Cuentas por Cobrar USD",
            tipo_cuenta=CuentaContable.TipoCuenta.ACTIVO,
            acepta_movimientos=True,
        )
        result = ContabilidadService._buscar_cuenta("1.1.02.02")
        assert result == cuenta

    def test_fallback_prefix(self, agencia_premium):
        CuentaContable.objects.create(
            codigo="1.1.02.99",
            nombre="Otras CxC",
            tipo_cuenta=CuentaContable.TipoCuenta.ACTIVO,
            acepta_movimientos=True,
        )
        result = ContabilidadService._buscar_cuenta("1.1.02.XX")
        assert result is not None
        assert result.codigo.startswith("1.1.02")

    def test_not_found_raises(self, agencia_premium):
        with pytest.raises(ValueError, match="No encontrada"):
            ContabilidadService._buscar_cuenta("9.9.99.99")


@pytest.mark.django_db
class TestGenerarLineasIntermediacion:
    def test_creates_entries(self, agencia_premium):
        from apps.finance.models import Factura

        _cuenta_cxc = CuentaContable.objects.create(
            codigo="1.1.02.02",
            nombre="CxC USD",
            tipo_cuenta=CuentaContable.TipoCuenta.ACTIVO,
            acepta_movimientos=True,
        )
        _cuenta_ingreso = CuentaContable.objects.create(
            codigo="4.1.01",
            nombre="Comisiones",
            tipo_cuenta=CuentaContable.TipoCuenta.INGRESO,
            acepta_movimientos=True,
        )
        _cuenta_cxp = CuentaContable.objects.create(
            codigo="2.1.01.02",
            nombre="CxP USD",
            tipo_cuenta=CuentaContable.TipoCuenta.PASIVO,
            acepta_movimientos=True,
        )
        _cuenta_iva = CuentaContable.objects.create(
            codigo="2.1.02.01",
            nombre="IVA Débito",
            tipo_cuenta=CuentaContable.TipoCuenta.PASIVO,
            acepta_movimientos=True,
        )
        _cuenta_igtf = CuentaContable.objects.create(
            codigo="2.1.02.03",
            nombre="IGTF",
            tipo_cuenta=CuentaContable.TipoCuenta.PASIVO,
            acepta_movimientos=True,
        )

        factura = Factura(
            numero_factura="F-001",
            tipo_factura=Factura.TipoFactura.TERCEROS,
            base_imponible=Decimal("100"),
            monto_iva_16=Decimal("16"),
            monto_igtf=Decimal("3"),
            monto_total=Decimal("119"),
            iva_monto=Decimal("16"),
            igtf_monto=Decimal("3"),
        )

        asiento = AsientoContable.objects.create(agencia=agencia_premium, glosa="test")
        ContabilidadService._generar_lineas_intermediacion(asiento, factura, Decimal("50"))

        movs = MovimientoContable.objects.filter(asiento=asiento).order_by("pk")
        assert movs.count() >= 2
        debitos = movs.filter(tipo=MovimientoContable.TipoMovimiento.DEBITO)
        creditos = movs.filter(tipo=MovimientoContable.TipoMovimiento.CREDITO)
        assert debitos.count() == 1
        assert creditos.count() >= 1

        total_debito_usd = sum(m.monto_usd for m in debitos)
        total_credito_usd = sum(m.monto_usd for m in creditos)
        assert abs(total_debito_usd - total_credito_usd) < Decimal("0.01")


@pytest.mark.django_db
class TestGenerarLineasVentaPropia:
    def test_creates_entries(self, agencia_premium):
        from apps.finance.models import Factura

        for codigo, nombre, tipo in [
            ("1.1.02.02", "CxC USD", CuentaContable.TipoCuenta.ACTIVO),
            ("4.2", "Ingresos", CuentaContable.TipoCuenta.INGRESO),
            ("2.1.02.01", "IVA Débito", CuentaContable.TipoCuenta.PASIVO),
            ("2.1.02.03", "IGTF", CuentaContable.TipoCuenta.PASIVO),
        ]:
            CuentaContable.objects.create(
                codigo=codigo,
                nombre=nombre,
                tipo_cuenta=tipo,
                acepta_movimientos=True,
            )

        factura = Factura(
            numero_factura="F-002",
            tipo_factura=Factura.TipoFactura.PRINCIPAL,
            base_imponible=Decimal("200"),
            base_exenta=Decimal("0"),
            monto_iva_16=Decimal("32"),
            monto_igtf=Decimal("6"),
            monto_total=Decimal("238"),
            iva_monto=Decimal("32"),
            igtf_monto=Decimal("6"),
        )

        asiento = AsientoContable.objects.create(agencia=agencia_premium, glosa="test-venta-propia")
        ContabilidadService._generar_lineas_venta_propia(asiento, factura, Decimal("50"))

        movs = MovimientoContable.objects.filter(asiento=asiento)
        assert movs.count() >= 2
        debito_usd = sum(
            m.monto_usd for m in movs.filter(tipo=MovimientoContable.TipoMovimiento.DEBITO)
        )
        credito_usd = sum(
            m.monto_usd for m in movs.filter(tipo=MovimientoContable.TipoMovimiento.CREDITO)
        )
        assert abs(debito_usd - credito_usd) < Decimal("0.01")

    def test_igtf_zero_skips_entry(self, agencia_premium):
        from apps.finance.models import Factura

        for codigo, nombre, tipo in [
            ("1.1.02.02", "CxC USD", CuentaContable.TipoCuenta.ACTIVO),
            ("4.2", "Ingresos", CuentaContable.TipoCuenta.INGRESO),
            ("2.1.02.01", "IVA Débito", CuentaContable.TipoCuenta.PASIVO),
            ("2.1.02.03", "IGTF", CuentaContable.TipoCuenta.PASIVO),
        ]:
            CuentaContable.objects.create(
                codigo=codigo,
                nombre=nombre,
                tipo_cuenta=tipo,
                acepta_movimientos=True,
            )

        factura = Factura(
            numero_factura="F-003",
            tipo_factura=Factura.TipoFactura.PRINCIPAL,
            base_imponible=Decimal("100"),
            base_exenta=Decimal("0"),
            monto_iva_16=Decimal("16"),
            monto_igtf=Decimal("0"),
            monto_total=Decimal("116"),
            iva_monto=Decimal("16"),
            igtf_monto=Decimal("0"),
        )

        asiento = AsientoContable.objects.create(agencia=agencia_premium, glosa="test-no-igtf")
        ContabilidadService._generar_lineas_venta_propia(asiento, factura, Decimal("50"))

        igtf_mov = MovimientoContable.objects.filter(
            asiento=asiento,
            cuenta__codigo="2.1.02.03",
        )
        assert igtf_mov.count() == 0


@pytest.mark.django_db
class TestProveedorInatur:
    def test_provisionar_creates_asiento(self, agencia_premium):
        _cuenta_gasto = CuentaContable.objects.create(
            codigo="6.1.05",
            nombre="Gasto INATUR",
            tipo_cuenta=CuentaContable.TipoCuenta.GASTO,
            acepta_movimientos=True,
        )
        _cuenta_pasivo = CuentaContable.objects.create(
            codigo="2.1.02.02",
            nombre="INATUR x Pagar",
            tipo_cuenta=CuentaContable.TipoCuenta.PASIVO,
            acepta_movimientos=True,
        )
        cuenta_ingreso = CuentaContable.objects.create(
            codigo="4.1.01",
            nombre="Ingresos",
            tipo_cuenta=CuentaContable.TipoCuenta.INGRESO,
            acepta_movimientos=True,
        )

        asiento_base = AsientoContable.objects.create(
            agencia=agencia_premium,
            glosa="base",
            fecha_contable="2026-06-15",
            estado=AsientoContable.EstadoAsiento.CONTABILIZADO,
        )
        MovimientoContable.objects.create(
            asiento=asiento_base,
            cuenta=cuenta_ingreso,
            tipo=MovimientoContable.TipoMovimiento.CREDITO,
            monto_usd=Decimal("1000"),
            monto_ves=Decimal("50000"),
        )

        asiento = ContabilidadService.provisionar_contribucion_inatur(6, 2026)
        assert asiento is not None
        assert asiento.tipo_asiento == AsientoContable.TipoAsiento.AJUSTE
        movs = MovimientoContable.objects.filter(asiento=asiento)
        assert movs.count() == 2
        assert movs.filter(tipo=MovimientoContable.TipoMovimiento.DEBITO).count() == 1
        assert movs.filter(tipo=MovimientoContable.TipoMovimiento.CREDITO).count() == 1

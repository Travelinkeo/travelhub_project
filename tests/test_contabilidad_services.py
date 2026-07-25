"""Tests para servicios de contabilidad integrada VEN-NIF."""

from datetime import date
from decimal import Decimal
from unittest.mock import patch

import pytest

from apps.contabilidad.models import (
    AsientoContable,
    CuentaContable,
    MovimientoContable,
)
from apps.contabilidad.services import ContabilidadService, _acreditar, _debitar

pytestmark = pytest.mark.django_db


@pytest.mark.django_db
class TestHelpers:
    """Test Helpers."""
    def test_debitar_creates_debito(self, agencia_premium):
        """Debitar creates debito."""
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
        """Acreditar creates credito."""
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
    """Test Buscar Cuenta."""
    def test_exact_match(self, agencia_premium):
        """Exact match."""
        cuenta = CuentaContable.objects.create(
            codigo="1.1.02.02",
            nombre="Cuentas por Cobrar USD",
            tipo_cuenta=CuentaContable.TipoCuenta.ACTIVO,
            acepta_movimientos=True,
        )
        result = ContabilidadService._buscar_cuenta("1.1.02.02")
        assert result == cuenta

    def test_fallback_prefix(self, agencia_premium):
        """Fallback prefix."""
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
        """Not found raises."""
        with pytest.raises(ValueError, match="No encontrada"):
            ContabilidadService._buscar_cuenta("9.9.99.99")


@pytest.mark.django_db
class TestGenerarLineasIntermediacion:
    """Test Generar Lineas Intermediacion."""
    def test_creates_entries(self, agencia_premium):
        """Creates entries."""
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
    """Test Generar Lineas Venta Propia."""
    def test_creates_entries(self, agencia_premium):
        """Creates entries."""
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
        """Igtf zero skips entry."""
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
    """Test Proveedor Inatur."""
    def test_provisionar_creates_asiento(self, agencia_premium):
        """Provisionar creates asiento."""
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


class TestObtenerTasaBCV:
    """Test Obtener Tasa Bcv."""
    def test_tasa_exacta(self, agencia_premium):
        """Tasa exacta."""
        from apps.finance.models import TasaCambioBCV

        TasaCambioBCV.objects.create(
            fecha=date(2026, 6, 15),
            tasa_bsd_por_usd=Decimal("50.00"),
            fuente="BCV",
        )
        tasa = ContabilidadService.obtener_tasa_bcv(date(2026, 6, 15))
        assert tasa == Decimal("50.00")

    def test_tasa_fallback_fecha_cercana(self, agencia_premium):
        """Tasa fallback fecha cercana."""
        from apps.finance.models import TasaCambioBCV

        TasaCambioBCV.objects.create(
            fecha=date(2026, 6, 14),
            tasa_bsd_por_usd=Decimal("49.50"),
            fuente="BCV",
        )
        tasa = ContabilidadService.obtener_tasa_bcv(date(2026, 6, 15))
        assert tasa == Decimal("49.50")

    def test_tasa_sin_datos_raise(self):
        """Tasa sin datos raise."""
        with pytest.raises(ValueError, match="No hay tasa BCV"):
            ContabilidadService.obtener_tasa_bcv(date(2026, 1, 1))


class TestGenerarAsientoDesdeFactura:
    """Test Generar Asiento Desde Factura."""
    def _setup_cuentas(self):
        """Setup cuentas."""
        CuentaContable.objects.create(
            codigo="1.1.02.02",
            nombre="CxC USD",
            tipo_cuenta=CuentaContable.TipoCuenta.ACTIVO,
            acepta_movimientos=True,
        )
        CuentaContable.objects.create(
            codigo="4.1.01",
            nombre="Comisiones",
            tipo_cuenta=CuentaContable.TipoCuenta.INGRESO,
            acepta_movimientos=True,
        )
        CuentaContable.objects.create(
            codigo="2.1.01.02",
            nombre="CxP USD",
            tipo_cuenta=CuentaContable.TipoCuenta.PASIVO,
            acepta_movimientos=True,
        )
        CuentaContable.objects.create(
            codigo="2.1.02.01",
            nombre="IVA Débito",
            tipo_cuenta=CuentaContable.TipoCuenta.PASIVO,
            acepta_movimientos=True,
        )
        CuentaContable.objects.create(
            codigo="2.1.02.03",
            nombre="IGTF",
            tipo_cuenta=CuentaContable.TipoCuenta.PASIVO,
            acepta_movimientos=True,
        )
        CuentaContable.objects.create(
            codigo="4.2",
            nombre="Ingresos Ventas",
            tipo_cuenta=CuentaContable.TipoCuenta.INGRESO,
            acepta_movimientos=True,
        )

    def test_genera_asiento_intermediacion(self, agencia_premium):
        """Genera asiento intermediacion."""
        from apps.finance.models import Factura

        self._setup_cuentas()
        factura = Factura.objects.create(
            agencia=agencia_premium,
            numero_factura="F-INTER-001",
            tipo_factura=Factura.TipoFactura.TERCEROS,
            base_imponible=Decimal("100"),
            monto_iva_16=Decimal("16"),
            monto_igtf=Decimal("3"),
            monto_total=Decimal("119"),
            iva_monto=Decimal("16"),
            igtf_monto=Decimal("3"),
            tasa_cambio=Decimal("50"),
        )
        with patch.object(ContabilidadService, "obtener_tasa_bcv", return_value=Decimal("50")):
            asiento = ContabilidadService.generar_asiento_desde_factura(factura)
        assert asiento is not None
        assert asiento.tipo_asiento == AsientoContable.TipoAsiento.VENTAS
        movs = MovimientoContable.objects.filter(asiento=asiento)
        assert movs.count() >= 4
        debito_total = sum(
            m.monto_usd for m in movs.filter(tipo=MovimientoContable.TipoMovimiento.DEBITO)
        )
        credito_total = sum(
            m.monto_usd for m in movs.filter(tipo=MovimientoContable.TipoMovimiento.CREDITO)
        )
        assert abs(debito_total - credito_total) < Decimal("0.01")

    def test_genera_asiento_venta_propia(self, agencia_premium):
        """Genera asiento venta propia."""
        from apps.finance.models import Factura

        self._setup_cuentas()
        factura = Factura.objects.create(
            agencia=agencia_premium,
            numero_factura="F-PROPIA-001",
            tipo_factura=Factura.TipoFactura.PRINCIPAL,
            base_imponible=Decimal("200"),
            monto_iva_16=Decimal("32"),
            monto_igtf=Decimal("6"),
            monto_total=Decimal("238"),
            iva_monto=Decimal("32"),
            igtf_monto=Decimal("6"),
            tasa_cambio=Decimal("50"),
        )
        with patch.object(ContabilidadService, "obtener_tasa_bcv", return_value=Decimal("50")):
            asiento = ContabilidadService.generar_asiento_desde_factura(factura)
        assert asiento is not None
        movs = MovimientoContable.objects.filter(asiento=asiento)
        debito_total = sum(
            m.monto_usd for m in movs.filter(tipo=MovimientoContable.TipoMovimiento.DEBITO)
        )
        credito_total = sum(
            m.monto_usd for m in movs.filter(tipo=MovimientoContable.TipoMovimiento.CREDITO)
        )
        assert abs(debito_total - credito_total) < Decimal("0.01")

    def test_asiento_reentrante_actualiza(self, agencia_premium):
        """Asiento reentrante actualiza."""
        from apps.finance.models import Factura

        self._setup_cuentas()
        factura = Factura.objects.create(
            agencia=agencia_premium,
            numero_factura="F-REEN-001",
            tipo_factura=Factura.TipoFactura.PRINCIPAL,
            base_imponible=Decimal("100"),
            monto_iva_16=Decimal("16"),
            monto_total=Decimal("116"),
            iva_monto=Decimal("16"),
            tasa_cambio=Decimal("50"),
        )
        with patch.object(ContabilidadService, "obtener_tasa_bcv", return_value=Decimal("50")):
            asiento1 = ContabilidadService.generar_asiento_desde_factura(factura)
            asiento2 = ContabilidadService.generar_asiento_desde_factura(factura)
        assert asiento1.id == asiento2.id
        movs = MovimientoContable.objects.filter(asiento=asiento1)
        assert movs.count() >= 3


class TestRegistrarPagoYDiferencial:
    """Test Registrar Pago Ydiferencial."""
    def _setup_cuentas(self):
        """ setup cuentas."""
        CuentaContable.objects.create(
            codigo="1.1.01.04",
            nombre="Banco",
            tipo_cuenta=CuentaContable.TipoCuenta.ACTIVO,
            acepta_movimientos=True,
        )
        CuentaContable.objects.create(
            codigo="1.1.02.02",
            nombre="CxC USD",
            tipo_cuenta=CuentaContable.TipoCuenta.ACTIVO,
            acepta_movimientos=True,
        )
        CuentaContable.objects.create(
            codigo="7.1.01",
            nombre="Ganancia Cambiaria",
            tipo_cuenta=CuentaContable.TipoCuenta.INGRESO,
            acepta_movimientos=True,
        )
        CuentaContable.objects.create(
            codigo="7.2.01",
            nombre="Pérdida Cambiaria",
            tipo_cuenta=CuentaContable.TipoCuenta.GASTO,
            acepta_movimientos=True,
        )
        CuentaContable.objects.create(
            codigo="2.1.02.01",
            nombre="IVA Débito",
            tipo_cuenta=CuentaContable.TipoCuenta.PASIVO,
            acepta_movimientos=True,
        )

    def test_registra_pago_sin_diferencial(self, agencia_premium, moneda_usd):
        """Registra pago sin diferencial."""
        from apps.bookings.models import PagoVenta, Venta

        self._setup_cuentas()
        venta = Venta.objects.create(
            agencia=agencia_premium,
            moneda=moneda_usd,
            total_venta=Decimal("500"),
            saldo_pendiente=Decimal("0"),
        )
        pago = PagoVenta.objects.create(
            agencia=agencia_premium, venta=venta, monto=Decimal("500"), moneda=moneda_usd
        )
        with patch.object(ContabilidadService, "obtener_tasa_bcv", return_value=Decimal("50")):
            asiento = ContabilidadService.registrar_pago_y_diferencial(pago)
        assert asiento is not None
        assert asiento.tipo_asiento == AsientoContable.TipoAsiento.DIARIO

    def test_registra_pago_sin_factura_retorna_none(self, agencia_premium, moneda_usd):
        """Registra pago sin factura retorna none."""
        from apps.bookings.models import PagoVenta, Venta

        venta = Venta.objects.create(
            agencia=agencia_premium,
            moneda=moneda_usd,
            total_venta=Decimal("500"),
            saldo_pendiente=Decimal("500"),
        )
        pago = PagoVenta.objects.create(
            agencia=agencia_premium, venta=venta, monto=Decimal("100"), moneda=moneda_usd
        )
        result = ContabilidadService.registrar_pago_y_diferencial(pago)
        assert result is None

    def test_registra_pago_con_ganancia_cambiaria(self, agencia_premium, moneda_usd):
        """Registra pago con ganancia cambiaria."""
        from apps.bookings.models import PagoVenta, Venta
        from apps.finance.models import Factura

        self._setup_cuentas()
        venta = Venta.objects.create(
            agencia=agencia_premium,
            moneda=moneda_usd,
            total_venta=Decimal("1000"),
            saldo_pendiente=Decimal("0"),
        )
        factura = Factura.objects.create(
            agencia=agencia_premium,
            numero_factura="F-GAN-001",
            tipo_factura=Factura.TipoFactura.PRINCIPAL,
            base_imponible=Decimal("1000"),
            monto_total=Decimal("1000"),
            tasa_cambio=Decimal("40"),
            cliente=None,
        )
        venta.factura = factura
        venta.save()
        pago = PagoVenta.objects.create(
            agencia=agencia_premium, venta=venta, monto=Decimal("1000"), moneda=moneda_usd
        )
        with patch.object(ContabilidadService, "obtener_tasa_bcv", return_value=Decimal("50")):
            asiento = ContabilidadService.registrar_pago_y_diferencial(pago)
        assert asiento is not None
        assert MovimientoContable.objects.filter(asiento=asiento, cuenta__codigo="7.1.01").exists()


class TestGenerarNotaDebitoDiferencial:
    """Test Generar Nota Debito Diferencial."""
    def test_genera_nota_debito_con_iva(self, agencia_premium, moneda_usd):
        """Genera nota debito con iva."""
        from apps.finance.models import Factura

        factura = Factura.objects.create(
            agencia=agencia_premium,
            numero_factura="F-ND-001",
            tipo_factura=Factura.TipoFactura.PRINCIPAL,
            base_imponible=Decimal("500"),
            monto_total=Decimal("500"),
            moneda=moneda_usd,
            tasa_cambio=Decimal("50"),
            cliente=None,
        )
        nd = ContabilidadService._generar_nota_debito_diferencial(
            factura=factura,
            pago=None,
            ganancia_bsd=Decimal("100"),
            tasa_factura=Decimal("50"),
            tasa_pago=Decimal("55"),
        )
        assert nd is not None
        assert nd.tipo_factura == Factura.TipoFactura.NOTA_DEBITO
        assert nd.iva_monto > 0

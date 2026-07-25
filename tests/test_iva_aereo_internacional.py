# tests/test_iva_aereo_internacional.py
"""
Tests para verificar la correcta aplicación de la alícuota de IVA del 50/50
para pasajes aéreos internacionales en cumplimiento con la Ley del IVA (2026).
"""

from decimal import Decimal

from django.test import TestCase

from apps.bookings.models import BoletoImportado
from apps.common.models import Moneda
from apps.crm.models import Cliente
from apps.finance.models_stubs import FacturaConsolidada, ItemFacturaConsolidada
from apps.finance.services.tax_eligibility import es_itinerario_internacional


class TestIVAInternacional(TestCase):
    """Tests para verificar IVA aéreo internacional (50% base imponible, 50% exento)"""

    def setUp(self):
        """SetUp."""
        self.moneda_usd = Moneda.objects.get_or_create(
            codigo_iso="USD", defaults={"nombre": "Dólar Estadounidense", "simbolo": "$"}
        )[0]

        self.cliente = Cliente.objects.create(
            nombres="Pedro",
            apellidos="Pérez",
            cedula_identidad="V-87654321",
            email="pedro@example.com",
        )

    def test_calculo_iva_aereo_internacional_50_50(self):
        """
        Valida que un pasaje aéreo internacional (precio $1000) divida su base:
        - $500 base gravada (a alícuota del 16% = $80 IVA)
        - $500 base exenta
        - Total = $1080
        """
        factura = FacturaConsolidada.objects.create(
            cliente=self.cliente,
            moneda=self.moneda_usd,
            emisor_rif="J-12345678-9",
            emisor_razon_social="Test Agencia C.A.",
            emisor_direccion_fiscal="Caracas, Venezuela",
            cliente_identificacion="V-87654321",
            tipo_operacion=FacturaConsolidada.TipoOperacion.VENTA_PROPIA,
            moneda_operacion=FacturaConsolidada.MonedaOperacion.DIVISA,
            tasa_cambio_bcv=Decimal("36.00"),
        )

        # Crear item de transporte aéreo internacional
        ItemFacturaConsolidada.objects.create(
            factura=factura,
            descripcion="Boleto CCS - MIA - CCS",
            cantidad=1,
            precio_unitario=Decimal("1000.00"),
            tipo_servicio=ItemFacturaConsolidada.TipoServicio.TRANSPORTE_AEREO_INTERNACIONAL,
            es_gravado=True,
            alicuota_iva=Decimal("16.00"),
        )

        factura.calcular_impuestos_venezuela()

        # Verificar bases y totales
        self.assertEqual(factura.subtotal_base_gravada, Decimal("500.00"))
        self.assertEqual(factura.subtotal_exento, Decimal("500.00"))
        self.assertEqual(factura.monto_iva_16, Decimal("80.00"))
        self.assertEqual(factura.monto_total, Decimal("1080.00"))

    def test_es_itinerario_internacional_helper(self):
        """
        Valida que el helper es_itinerario_internacional reconozca correctamente
        vuelos nacionales e internacionales a partir de datos estructurados e itinerarios.
        """
        # Caso 1: Vuelo nacional estructurado (CCS a PMV)
        boleto_nac = BoletoImportado(
            ruta_vuelo="CCS-PMV", datos_parseados={"vuelos": [{"origen": "CCS", "destino": "PMV"}]}
        )
        self.assertFalse(es_itinerario_internacional(boleto_nac))

        # Caso 2: Vuelo internacional estructurado (CCS a MIA)
        boleto_int = BoletoImportado(
            ruta_vuelo="CCS-MIA", datos_parseados={"vuelos": [{"origen": "CCS", "destino": "MIA"}]}
        )
        self.assertTrue(es_itinerario_internacional(boleto_int))

        # Caso 3: Vuelo nacional fallback de texto (CCS-MAR)
        boleto_nac_text = BoletoImportado(ruta_vuelo="CCS-MAR", datos_parseados={})
        self.assertFalse(es_itinerario_internacional(boleto_nac_text))

        # Caso 4: Vuelo internacional fallback de texto (CCS-PTY)
        boleto_int_text = BoletoImportado(ruta_vuelo="CCS-PTY", datos_parseados={})
        self.assertTrue(es_itinerario_internacional(boleto_int_text))

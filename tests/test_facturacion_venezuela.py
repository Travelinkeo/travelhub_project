# tests/test_facturacion_venezuela.py
"""
Tests para el sistema de facturación venezolana.
Valida cálculos fiscales con la nueva alícuota del 25% y retrocompatibilidad del 16%.
"""

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.common.models import Moneda
from apps.crm.models import Cliente
from apps.finance.models_stubs import (
    DocumentoExportacionConsolidado,
    FacturaConsolidada,
    ItemFacturaConsolidada,
)


class TestFacturaConsolidada(TestCase):
    """Tests para el modelo FacturaConsolidada (unificado bajo la tabla Factura)"""

    def setUp(self):
        """Configuración inicial para tests"""
        """SetUp."""
        self.moneda_usd = Moneda.objects.get_or_create(
            codigo_iso="USD", defaults={"nombre": "Dólar Estadounidense", "simbolo": "$"}
        )[0]

        self.moneda_bs = Moneda.objects.get_or_create(
            codigo_iso="VES",
            defaults={"nombre": "Bolívar Soberano", "simbolo": "Bs.", "es_moneda_local": True},
        )[0]

        self.cliente = Cliente.objects.create(
            nombres="Juan",
            apellidos="Pérez",
            cedula_identidad="V-12345678",
            email="juan@example.com",
        )

    def test_crear_factura_venezuela_basica(self):
        """Test creación básica de factura venezolana"""
        factura = FacturaConsolidada.objects.create(
            cliente=self.cliente,
            moneda=self.moneda_usd,
            emisor_rif="J-12345678-9",
            emisor_razon_social="Test Agencia C.A.",
            emisor_direccion_fiscal="Caracas, Venezuela",
            cliente_identificacion="V-12345678",
            tipo_operacion=FacturaConsolidada.TipoOperacion.VENTA_PROPIA,
            moneda_operacion=FacturaConsolidada.MonedaOperacion.DIVISA,
            tasa_cambio_bcv=Decimal("37.50"),
        )

        self.assertEqual(factura.emisor_rif, "J-12345678-9")
        self.assertEqual(factura.tipo_operacion, FacturaConsolidada.TipoOperacion.VENTA_PROPIA)
        self.assertEqual(factura.moneda_operacion, FacturaConsolidada.MonedaOperacion.DIVISA)
        self.assertTrue(factura.cliente_es_residente)

    def test_calculo_iva_servicio_gravado_25(self):
        """Test cálculo de IVA para servicios gravados con la alícuota general de 25% (Normativa 2026)"""
        factura = FacturaConsolidada.objects.create(
            cliente=self.cliente,
            moneda=self.moneda_usd,
            emisor_rif="J-12345678-9",
            emisor_razon_social="Test Agencia C.A.",
            emisor_direccion_fiscal="Caracas, Venezuela",
            cliente_identificacion="V-12345678",
            tipo_operacion=FacturaConsolidada.TipoOperacion.VENTA_PROPIA,
            moneda_operacion=FacturaConsolidada.MonedaOperacion.DIVISA,
            tasa_cambio_bcv=Decimal("36.00"),
        )

        # Crear item gravado al 25%
        ItemFacturaConsolidada.objects.create(
            factura=factura,
            descripcion="Alojamiento Hotel Premium",
            cantidad=1,
            precio_unitario=Decimal("100.00"),
            tipo_servicio=ItemFacturaConsolidada.TipoServicio.ALOJAMIENTO_Y_OTROS_GRAVADOS,
            es_gravado=True,
            alicuota_iva=Decimal("25.00"),
        )

        factura.calcular_impuestos_venezuela()

        self.assertEqual(factura.subtotal_base_gravada, Decimal("100.00"))
        self.assertEqual(
            factura.monto_iva_16, Decimal("25.00")
        )  # En el modelo unificado se mapea la alícuota general a este campo para mantener consistencia con los esquemas antiguos
        self.assertEqual(factura.monto_total, Decimal("125.00"))

    def test_calculo_iva_servicio_gravado_16_legacy(self):
        """Test cálculo de IVA para servicios gravados con la alícuota general legacy del 16%"""
        factura = FacturaConsolidada.objects.create(
            cliente=self.cliente,
            moneda=self.moneda_usd,
            emisor_rif="J-12345678-9",
            emisor_razon_social="Test Agencia C.A.",
            emisor_direccion_fiscal="Caracas, Venezuela",
            cliente_identificacion="V-12345678",
            tipo_operacion=FacturaConsolidada.TipoOperacion.VENTA_PROPIA,
            moneda_operacion=FacturaConsolidada.MonedaOperacion.DIVISA,
            tasa_cambio_bcv=Decimal("36.00"),
        )

        # Crear item gravado al 16% (retrocompatibilidad)
        ItemFacturaConsolidada.objects.create(
            factura=factura,
            descripcion="Alojamiento Hotel Legacy",
            cantidad=1,
            precio_unitario=Decimal("100.00"),
            tipo_servicio=ItemFacturaConsolidada.TipoServicio.ALOJAMIENTO_Y_OTROS_GRAVADOS,
            es_gravado=True,
            alicuota_iva=Decimal("16.00"),
        )

        factura.calcular_impuestos_venezuela()

        self.assertEqual(factura.subtotal_base_gravada, Decimal("100.00"))
        self.assertEqual(factura.monto_iva_16, Decimal("16.00"))
        self.assertEqual(factura.monto_total, Decimal("116.00"))

    def test_calculo_servicio_exento(self):
        """Test cálculo para servicios exentos (transporte aéreo nacional)"""
        factura = FacturaConsolidada.objects.create(
            cliente=self.cliente,
            moneda=self.moneda_usd,
            emisor_rif="J-12345678-9",
            emisor_razon_social="Test Agencia C.A.",
            emisor_direccion_fiscal="Caracas, Venezuela",
            cliente_identificacion="V-12345678",
            tipo_operacion=FacturaConsolidada.TipoOperacion.VENTA_PROPIA,
            moneda_operacion=FacturaConsolidada.MonedaOperacion.DIVISA,
            tasa_cambio_bcv=Decimal("36.00"),
        )

        # Crear item exento
        ItemFacturaConsolidada.objects.create(
            factura=factura,
            descripcion="Boleto Aéreo CCS-PMV",
            cantidad=1,
            precio_unitario=Decimal("150.00"),
            tipo_servicio=ItemFacturaConsolidada.TipoServicio.TRANSPORTE_AEREO_NACIONAL,
            es_gravado=False,
            alicuota_iva=Decimal("0.00"),
        )

        factura.calcular_impuestos_venezuela()

        self.assertEqual(factura.subtotal_exento, Decimal("150.00"))
        self.assertEqual(factura.monto_iva_16, Decimal("0.00"))
        self.assertEqual(factura.monto_total, Decimal("150.00"))

    def test_calculo_igtf_spe(self):
        """Test cálculo de IGTF para Sujeto Pasivo Especial"""
        factura = FacturaConsolidada.objects.create(
            cliente=self.cliente,
            moneda=self.moneda_usd,
            emisor_rif="J-12345678-9",
            emisor_razon_social="Test Agencia C.A.",
            emisor_direccion_fiscal="Caracas, Venezuela",
            cliente_identificacion="V-12345678",
            tipo_operacion=FacturaConsolidada.TipoOperacion.VENTA_PROPIA,
            moneda_operacion=FacturaConsolidada.MonedaOperacion.DIVISA,
            tasa_cambio_bcv=Decimal("36.00"),
            es_sujeto_pasivo_especial=True,
        )

        # Crear item gravado al 25%
        ItemFacturaConsolidada.objects.create(
            factura=factura,
            descripcion="Servicio Turístico",
            cantidad=1,
            precio_unitario=Decimal("100.00"),
            tipo_servicio=ItemFacturaConsolidada.TipoServicio.ALOJAMIENTO_Y_OTROS_GRAVADOS,
            es_gravado=True,
            alicuota_iva=Decimal("25.00"),
        )

        factura.calcular_impuestos_venezuela()

        # Base IGTF = Subtotal + IVA = 100 + 25 = 125
        # IGTF = 125 * 0.03 = 3.75
        self.assertEqual(factura.monto_igtf, Decimal("3.75"))
        self.assertEqual(factura.monto_total, Decimal("128.75"))

    def test_calculo_equivalencias_bolivares(self):
        """Test cálculo de equivalencias en bolívares"""
        factura = FacturaConsolidada.objects.create(
            cliente=self.cliente,
            moneda=self.moneda_usd,
            emisor_rif="J-12345678-9",
            emisor_razon_social="Test Agencia C.A.",
            emisor_direccion_fiscal="Caracas, Venezuela",
            cliente_identificacion="V-12345678",
            tipo_operacion=FacturaConsolidada.TipoOperacion.VENTA_PROPIA,
            moneda_operacion=FacturaConsolidada.MonedaOperacion.DIVISA,
            tasa_cambio_bcv=Decimal("37.00"),
        )

        ItemFacturaConsolidada.objects.create(
            factura=factura,
            descripcion="Servicio Test",
            cantidad=1,
            precio_unitario=Decimal("100.00"),
            tipo_servicio=ItemFacturaConsolidada.TipoServicio.ALOJAMIENTO_Y_OTROS_GRAVADOS,
            alicuota_iva=Decimal("25.00"),
        )

        factura.calcular_impuestos_venezuela()

        # 100 USD * 37 = 3700 Bs
        self.assertEqual(factura.subtotal_base_gravada_bs, Decimal("3700.00"))
        # 25 USD * 37 = 925 Bs
        self.assertEqual(factura.monto_iva_16_bs, Decimal("925.00"))

    def test_validacion_datos_tercero_intermediacion(self):
        """Test validación de datos de tercero en intermediación"""
        factura = FacturaConsolidada(
            cliente=self.cliente,
            moneda=self.moneda_usd,
            emisor_rif="J-12345678-9",
            emisor_razon_social="Test Agencia C.A.",
            emisor_direccion_fiscal="Caracas, Venezuela",
            cliente_identificacion="V-12345678",
            tipo_operacion=FacturaConsolidada.TipoOperacion.INTERMEDIACION,
            moneda_operacion=FacturaConsolidada.MonedaOperacion.DIVISA,
            tasa_cambio_bcv=Decimal("36.00"),
            # Falta tercero_rif y tercero_razon_social
        )

        with self.assertRaises(ValidationError):
            factura.clean()

    def test_validacion_tasa_cambio_divisas(self):
        """Test validación de tasa de cambio para facturas en divisas"""
        factura = FacturaConsolidada(
            cliente=self.cliente,
            moneda=self.moneda_usd,
            emisor_rif="J-12345678-9",
            emisor_razon_social="Test Agencia C.A.",
            emisor_direccion_fiscal="Caracas, Venezuela",
            cliente_identificacion="V-12345678",
            tipo_operacion=FacturaConsolidada.TipoOperacion.VENTA_PROPIA,
            moneda_operacion=FacturaConsolidada.MonedaOperacion.DIVISA,
            # Falta tasa_cambio_bcv
        )

        with self.assertRaises(ValidationError):
            factura.clean()


class TestItemFacturaConsolidada(TestCase):
    """Tests para el modelo ItemFacturaConsolidada"""

    def setUp(self):
        """Setup."""
        self.moneda_usd = Moneda.objects.get_or_create(
            codigo_iso="USD", defaults={"nombre": "Dólar Estadounidense", "simbolo": "$"}
        )[0]

        self.cliente = Cliente.objects.create(
            nombres="Test", apellidos="Cliente", cedula_identidad="V-11111111"
        )

        self.factura = FacturaConsolidada.objects.create(
            cliente=self.cliente,
            moneda=self.moneda_usd,
            emisor_rif="J-12345678-9",
            emisor_razon_social="Test Agencia C.A.",
            emisor_direccion_fiscal="Caracas, Venezuela",
            cliente_identificacion="V-11111111",
            tipo_operacion=FacturaConsolidada.TipoOperacion.VENTA_PROPIA,
            moneda_operacion=FacturaConsolidada.MonedaOperacion.DIVISA,
            tasa_cambio_bcv=Decimal("36.00"),
        )

    def test_validacion_datos_boleto_aereo(self):
        """Test validación de datos obligatorios para boletos aéreos"""
        item = ItemFacturaConsolidada(
            factura=self.factura,
            descripcion="Boleto Aéreo",
            cantidad=1,
            precio_unitario=Decimal("200.00"),
            tipo_servicio=ItemFacturaConsolidada.TipoServicio.TRANSPORTE_AEREO_NACIONAL,
            # Faltan nombre_pasajero, numero_boleto, itinerario
        )

        with self.assertRaises(ValidationError):
            item.clean()

    def test_item_boleto_aereo_completo(self):
        """Test creación de item de boleto aéreo con datos completos"""
        item = ItemFacturaConsolidada.objects.create(
            factura=self.factura,
            descripcion="Boleto Aéreo CCS-PMV",
            cantidad=1,
            precio_unitario=Decimal("200.00"),
            tipo_servicio=ItemFacturaConsolidada.TipoServicio.TRANSPORTE_AEREO_NACIONAL,
            nombre_pasajero="Juan Pérez",
            numero_boleto="0577280309142",
            itinerario="CCS-PMV-CCS",
            codigo_aerolinea="LA",
        )

        self.assertEqual(item.nombre_pasajero, "Juan Pérez")
        self.assertEqual(item.numero_boleto, "0577280309142")
        self.assertEqual(item.itinerario, "CCS-PMV-CCS")


class TestDocumentoExportacionConsolidado(TestCase):
    """Tests para el modelo DocumentoExportacionConsolidado"""

    def setUp(self):
        """Setup."""
        self.moneda_usd = Moneda.objects.get_or_create(
            codigo_iso="USD", defaults={"nombre": "Dólar Estadounidense", "simbolo": "$"}
        )[0]

        self.cliente = Cliente.objects.create(
            nombres="John", apellidos="Smith", numero_pasaporte="US123456789"
        )

        self.factura = FacturaConsolidada.objects.create(
            cliente=self.cliente,
            moneda=self.moneda_usd,
            emisor_rif="J-12345678-9",
            emisor_razon_social="Test Agencia C.A.",
            emisor_direccion_fiscal="Caracas, Venezuela",
            cliente_identificacion="US123456789",
            cliente_es_residente=False,  # Cliente extranjero
            tipo_operacion=FacturaConsolidada.TipoOperacion.VENTA_PROPIA,
            moneda_operacion=FacturaConsolidada.MonedaOperacion.DIVISA,
            tasa_cambio_bcv=Decimal("36.00"),
        )

    def test_crear_documento_exportacion(self):
        """Test creación de documento de exportación"""
        documento = DocumentoExportacionConsolidado.objects.create(
            factura=self.factura, tipo_documento="PASAPORTE", numero_documento="US123456789"
        )

        self.assertEqual(documento.factura, self.factura)
        self.assertEqual(documento.tipo_documento, "PASAPORTE")
        self.assertEqual(documento.numero_documento, "US123456789")
        self.assertIsNotNone(documento.fecha_subida)

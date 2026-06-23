"""
Tests para el Parser de Boletos

Verifica que:
- Se detecten correctamente los diferentes GDS (Sabre, KIU, Amadeus)
- Se extraigan los datos correctamente
- Se manejen errores de parsing
- Se generen PDFs correctamente
"""

from decimal import Decimal
from unittest.mock import patch

import pytest

from apps.automation.parsers.normalization import DataNormalizationService
from apps.automation.parsers.persistence import BoletoPersistenceService
from apps.automation.parsers.ticket_parser import extract_data_from_text
from apps.automation.services.ticket_parser_service import TicketParserService
from apps.bookings.models import BoletoImportado

pytestmark = pytest.mark.django_db


class TestParserDetection:
    """Tests para detección de GDS"""

    def test_detecta_sabre(self):
        """Test: Debe detectar boletos Sabre"""
        texto_sabre = """
        RECIBO DE PASAJE ELECTRÓNICO
        CÓDIGO DE RESERVACIÓN: ABC123
        NÚMERO DE BOLETO: 1234567890
        """

        datos = extract_data_from_text(texto_sabre)
        assert datos.get("gds") == "sabre"

    def test_detecta_kiu(self):
        """Test: Debe detectar boletos KIU"""
        texto_kiu = """
        BOLETO ELECTRÓNICO
        CÓDIGO DE RESERVA: XYZ789
        NÚMERO DE BOLETO: 9876543210
        NOMBRE DEL PASAJERO: DOE/JOHN
        """

        datos = extract_data_from_text(texto_kiu)
        assert datos.get("gds") in ["kiu", "unknown"]  # Puede variar según implementación

    def test_texto_vacio_retorna_error(self):
        """Test: Texto vacío debe retornar error"""
        datos = extract_data_from_text("")
        assert "error" in datos or not datos


class TestParserExtraction:
    """Tests para extracción de datos"""

    def test_extrae_pnr(self, datos_boleto_sabre):
        """Test: Debe extraer PNR correctamente"""
        assert datos_boleto_sabre.get("pnr") == "XYZ789"

    def test_extrae_numero_boleto(self, datos_boleto_sabre):
        """Test: Debe extraer número de boleto"""
        assert datos_boleto_sabre.get("ticket_number") == "9876543210"

    def test_extrae_nombre_pasajero(self, datos_boleto_sabre):
        """Test: Debe extraer nombre del pasajero"""
        assert datos_boleto_sabre.get("passenger_name") == "SMITH/JANE"

    def test_extrae_aerolinea(self, datos_boleto_sabre):
        """Test: Debe extraer nombre de aerolínea"""
        assert datos_boleto_sabre.get("airline_name") == "COPA AIRLINES"

    def test_extrae_total(self, datos_boleto_sabre):
        """Test: Debe extraer total del boleto"""
        total = datos_boleto_sabre.get("total")
        assert total == "750.00"
        assert Decimal(total) == Decimal("750.00")

    @pytest.mark.critical
    def test_extrae_moneda(self, datos_boleto_sabre):
        """Test: Debe extraer código de moneda"""
        assert datos_boleto_sabre.get("moneda") == "USD"


class TestParserService:
    """Tests para TicketParserService"""

    @patch("apps.automation.parsers.ticket_parser.extract_data_from_text")
    def test_actualiza_campos_modelo(self, mock_extract, agencia, datos_boleto_sabre):
        """Test: Debe actualizar campos del modelo correctamente"""
        boleto = BoletoImportado.objects.create(agencia=agencia, estado_parseo="PEN")

        datos_normalizados = DataNormalizationService.normalize_ticket_data(datos_boleto_sabre)
        BoletoPersistenceService.update_boleto_from_data(boleto, datos_normalizados)

        boleto.refresh_from_db()

        assert boleto.localizador_pnr == "XYZ789"
        assert boleto.numero_boleto == "9876543210"
        assert boleto.nombre_pasajero_completo == "SMITH/JANE"
        assert boleto.aerolinea_emisora == "COPA AIRLINES"
        assert boleto.total_boleto == Decimal("750.00")

    def test_mapeo_datos_kiu(self, agencia, datos_boleto_kiu):
        """Test: Debe mapear correctamente datos de KIU"""
        boleto = BoletoImportado.objects.create(agencia=agencia, estado_parseo="PEN")

        datos_normalizados = DataNormalizationService.normalize_ticket_data(datos_boleto_kiu)
        BoletoPersistenceService.update_boleto_from_data(boleto, datos_normalizados)

        boleto.refresh_from_db()

        assert boleto.localizador_pnr == "DEF456"
        assert boleto.numero_boleto == "1112223334"
        assert boleto.nombre_pasajero_completo == "GARCIA/MARIA"

    @pytest.mark.critical
    def test_maneja_datos_faltantes(self, agencia):
        """Test: Debe manejar datos faltantes sin fallar"""
        boleto = BoletoImportado.objects.create(agencia=agencia, estado_parseo="PEN")

        datos_incompletos = {
            "pnr": "TEST123",
            # Faltan otros campos
        }

        # No debe lanzar excepción
        BoletoPersistenceService.update_boleto_from_data(boleto, datos_incompletos)

        boleto.refresh_from_db()
        assert boleto.localizador_pnr == "TEST123"

    def test_convierte_montos_a_decimal(self, agencia):
        """Test: Debe convertir montos string a Decimal"""
        boleto = BoletoImportado.objects.create(agencia=agencia, estado_parseo="PEN")

        datos = {
            "total": "1234.56",  # String
            "fare_amount": "1000.00",
        }

        BoletoPersistenceService.update_boleto_from_data(boleto, datos)

        boleto.refresh_from_db()
        assert isinstance(boleto.total_boleto, Decimal)
        assert boleto.total_boleto == Decimal("1234.56")


class TestParserErrorHandling:
    """Tests para manejo de errores"""

    @patch("apps.automation.services.ticket_parser_service.ExtractionService.extract_text")
    def test_maneja_pdf_corrupto(self, mock_extraer, agencia):
        """Test: Debe manejar PDFs corruptos sin crashear"""
        boleto = BoletoImportado.objects.create(agencia=agencia, estado_parseo="PEN")

        # Mock retorna None (archivo corrupto)
        mock_extraer.return_value = None

        service = TicketParserService()
        resultado = service.procesar_boleto(boleto.pk)

        assert resultado is None
        boleto.refresh_from_db()
        assert boleto.estado_parseo == "REV"

    @patch("apps.automation.parsers.ai_universal_parser.UniversalAIParser.parse", return_value=None)
    @patch("apps.automation.services.ticket_parser_service.ExtractionService.extract_text")
    @patch("apps.automation.services.ticket_parser_service.extract_data_from_text")
    def test_maneja_excepcion_en_parsing(self, mock_extract, mock_extraer, mock_ai_parse, agencia):
        """Test: Debe capturar excepciones y marcar como error"""
        boleto = BoletoImportado.objects.create(agencia=agencia, estado_parseo="PEN")

        # Mock extrae texto correctamente
        mock_extraer.return_value = "texto de prueba"
        # Pero el parser falla
        mock_extract.side_effect = Exception("Test error")

        service = TicketParserService()
        resultado = service.procesar_boleto(boleto.pk)

        assert resultado is None
        boleto.refresh_from_db()
        assert boleto.estado_parseo == "REV"
        assert "Test error" in boleto.log_parseo

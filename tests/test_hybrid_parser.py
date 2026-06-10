from unittest.mock import patch

import pytest

from apps.automation.services.ticket_parser_service import TicketParserService
from apps.bookings.models import BoletoImportado
from core.models import Agencia

# Use pytest-django
pytestmark = pytest.mark.django_db(transaction=True)

# Texto de un boleto genérico para pruebas de fallback
SAMPLE_SABRE_TICKET = """
DETALLE DE VIAJE Y BOLETO
PASAJERO: DOE/JOHN
LOCALIZADOR: R2D2C3
BOLETO: 1234567890123
ITINERARIO
1 AV 46 C 22MAY BOGMAD HK1 0700 2330
"""

# Respuesta de IA simulada
MOCK_AI_RESPONSE = {
    "NOMBRE_DEL_PASAJERO": "JOHN DOE",
    "SOLO_NOMBRE_PASAJERO": "JOHN",
    "CODIGO_IDENTIFICACION": "123456",
    "NUMERO_DE_BOLETO": "9876543210987",
    "FECHA_DE_EMISION": "2025-05-08",
    "CODIGO_RESERVA": "AI-R2D2",
    "CODIGO_RESERVA_AEROLINEA": "ANPHTO",
    "NOMBRE_AEROLINEA": "AVIANCA",
    "TARIFA_IMPORTE": 500.0,
    "TOTAL_IMPORTE": 550.0,
    "TOTAL_MONEDA": "USD",
    "itinerario": [
        {
            "aerolinea": "AVIANCA",
            "numero_vuelo": "AV 46",
            "origen": "BOGOTA",
            "codigo_iata_origen": "BOG",
            "destino": "MADRID",
            "codigo_iata_destino": "MAD",
            "fecha_salida": "22MAY25",
            "hora_salida": "07:00",
            "hora_llegada": "23:30",
            "clase": "BUSINESS",
            "localizador_aerolinea": "ANPHTO",
        }
    ],
}


class TestHybridParser:
    @patch("apps.automation.services.ticket_parser_service.extract_data_from_text")
    @patch("apps.automation.parsers.ai_universal_parser.UniversalAIParser.parse")
    def test_regex_first_strategy_success(self, mock_ai_parse, mock_extract_regex):
        """
        Verifica que si el Regex local devuelve un resultado completo y válido,
        se utiliza ese resultado y NO se llama a la IA.
        """
        mock_extract_regex.return_value = {
            "passenger_name": "JOHN DOE",
            "pnr": "R2D2C3",
            "numero_boleto": "1234567890123",
            "segments": [
                {
                    "aerolinea": "AVIANCA",
                    "numero_vuelo": "AV46",
                    "origen": "BOG",
                    "destino": "MAD",
                    "fecha": "22MAY25",
                    "hora_salida": "07:00",
                }
            ],
        }
        mock_ai_parse.return_value = MOCK_AI_RESPONSE.copy()

        agencia = Agencia.objects.create(nombre="Test Agency Regex Success")

        from django.core.files.base import ContentFile

        archivo_simulado = ContentFile(SAMPLE_SABRE_TICKET.encode("utf-8"), name="ticket.txt")

        boleto = BoletoImportado(
            agencia=agencia, archivo_boleto=archivo_simulado, estado_parseo="PEN"
        )
        boleto._skip_auto_parse = True
        boleto.save()

        # Procesar
        service = TicketParserService()
        venta = service.procesar_boleto(boleto.pk, bypass_cache=True, ignore_manual=True)

        boleto.refresh_from_db()

        assert venta is not None
        # La IA no debería ser llamada
        mock_ai_parse.assert_not_called()
        mock_extract_regex.assert_called_once()

        assert boleto.estado_parseo == "COM"
        assert boleto.numero_boleto == "1234567890123"
        assert boleto.localizador_pnr == "R2D2C3"
        assert boleto.nombre_pasajero_completo == "JOHN DOE"

    @patch("apps.automation.services.ticket_parser_service.extract_data_from_text")
    @patch("apps.automation.parsers.ai_universal_parser.UniversalAIParser.parse")
    def test_regex_first_fallback_on_failure(self, mock_ai_parse, mock_extract_regex):
        """
        Verifica que si el Regex local falla o devuelve un error, se ejecuta el fallback a la IA.
        """
        mock_extract_regex.return_value = {"error": "Formato no compatible"}
        mock_ai_parse.return_value = MOCK_AI_RESPONSE.copy()

        agencia = Agencia.objects.create(nombre="Test Agency Fallback Failure")
        from django.core.files.base import ContentFile

        archivo_simulado = ContentFile(SAMPLE_SABRE_TICKET.encode("utf-8"), name="ticket.txt")

        boleto = BoletoImportado(
            agencia=agencia, archivo_boleto=archivo_simulado, estado_parseo="PEN"
        )
        boleto._skip_auto_parse = True
        boleto.save()

        # Procesar
        service = TicketParserService()
        venta = service.procesar_boleto(boleto.pk, bypass_cache=True, ignore_manual=True)

        boleto.refresh_from_db()

        assert venta is not None
        mock_extract_regex.assert_called_once()
        mock_ai_parse.assert_called_once()

        assert boleto.estado_parseo == "COM"
        assert boleto.numero_boleto == "9876543210987"
        assert boleto.localizador_pnr == "AI-R2D2"

    @patch("apps.automation.services.ticket_parser_service.extract_data_from_text")
    @patch("apps.automation.parsers.ai_universal_parser.UniversalAIParser.parse")
    def test_regex_first_fallback_on_incomplete(self, mock_ai_parse, mock_extract_regex):
        """
        Verifica que si el Regex local extrae datos pero están incompletos (p. ej. sin segmentos de vuelo),
        el pipeline ejecuta el fallback a la IA.
        """
        # Datos incompletos: sin segmentos/vuelos
        mock_extract_regex.return_value = {
            "passenger_name": "JOHN DOE",
            "pnr": "R2D2C3",
            "numero_boleto": "1234567890123",
            "segments": [],
        }
        mock_ai_parse.return_value = MOCK_AI_RESPONSE.copy()

        agencia = Agencia.objects.create(nombre="Test Agency Fallback Incomplete")
        from django.core.files.base import ContentFile

        archivo_simulado = ContentFile(SAMPLE_SABRE_TICKET.encode("utf-8"), name="ticket.txt")

        boleto = BoletoImportado(
            agencia=agencia, archivo_boleto=archivo_simulado, estado_parseo="PEN"
        )
        boleto._skip_auto_parse = True
        boleto.save()

        # Procesar
        service = TicketParserService()
        venta = service.procesar_boleto(boleto.pk, bypass_cache=True, ignore_manual=True)

        boleto.refresh_from_db()

        assert venta is not None
        mock_extract_regex.assert_called_once()
        mock_ai_parse.assert_called_once()

        assert boleto.estado_parseo == "COM"
        assert boleto.numero_boleto == "9876543210987"
        assert boleto.localizador_pnr == "AI-R2D2"

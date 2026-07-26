from unittest.mock import patch

from apps.automation.parsers.base_parser import ParsedTicketData
from apps.automation.parsers.legacy.travelport_parser import TravelportParser

# Ticket Travelport completo que puede parsear por Regex
SAMPLE_TRAVELPORT_TICKET_REGEX = """
TRAVELPORT ELECTRONIC TICKET RECEIPT
BOOKING REFERENCE: ABC123
TICKET NUMBER: 1761234567890
PASSENGER: SMITH/JOHN
DATE OF ISSUE: 12 MAY 2026
FLIGHTS
1  LA 2415 Y 12MAY LIMCUZ HK1  0915 1035
"""

# Ticket Travelport incompleto que requiere AI reinforcement
SAMPLE_TRAVELPORT_TICKET_INCOMPLETE = """
TRAVELPORT ELECTRONIC TICKET RECEIPT
BOOKING REFERENCE: No encontrado
TICKET NUMBER: No encontrado
PASSENGER: SMITH/JOHN
"""

MOCK_AI_RESPONSE_TRAVELPORT = {
    "CODIGO_RESERVA": "ABC123",
    "NOMBRE_DEL_PASAJERO": "JOHN SMITH",
    "NUMERO_DE_BOLETO": "1761234567890",
    "FECHA_DE_EMISION": "2026-05-12",
    "TARIFA_IMPORTE": 300.0,
    "TOTAL_IMPORTE": 350.0,
    "TOTAL_MONEDA": "USD",
    "itinerario": [
        {
            "aerolinea": "LA",
            "numero_vuelo": "LA2415",
            "origen": "LIMA",
            "codigo_iata_origen": "LIM",
            "destino": "CUZCO",
            "codigo_iata_destino": "CUZ",
            "fecha_salida": "12MAY26",
            "hora_salida": "09:15",
            "hora_llegada": "10:35",
            "clase": "Y",
        }
    ],
}


class TestTravelportParser:
    """TestTravelportParser."""

    def test_can_parse_valid_travelport(self):
        """test_can_parse_valid_travelport."""
        parser = TravelportParser()
        # Caso 1: Travelport
        assert parser.can_parse("Some text with Travelport inside") is True
        # Caso 2: Galileo
        assert parser.can_parse("GALILEO GDS reservation details") is True
        # Caso 3: Electronic Ticket Receipt + ViewTrip
        assert parser.can_parse("ELECTRONIC TICKET RECEIPT\nVIEWTRIP DETAILS") is True

    def test_can_parse_invalid_travelport(self):
        """test_can_parse_invalid_travelport."""
        parser = TravelportParser()
        # Evitar colisión con KIUSYS
        assert parser.can_parse("KIUSYS SYSTEM ELECTRONIC TICKET RECEIPT") is False
        # Texto random sin marcadores
        assert parser.can_parse("Random airline ticket layout") is False

    def test_parse_complete_regex(self):
        """test_parse_complete_regex."""
        parser = TravelportParser()
        res = parser.parse(SAMPLE_TRAVELPORT_TICKET_REGEX)

        assert isinstance(res, ParsedTicketData)
        assert res.source_system == "TRAVELPORT"
        assert res.pnr == "ABC123"
        assert res.ticket_number == "1761234567890"
        assert res.passenger_name == "SMITH/JOHN"
        assert len(res.flights) == 1
        assert res.flights[0]["origen"] == "LIM"
        assert res.flights[0]["destino"] == "CUZ"
        assert res.flights[0]["numero_vuelo"] == "LA2415"

    @patch("apps.automation.parsers.ai_universal_parser.UniversalAIParser.parse")
    def test_parse_incomplete_triggers_ai_reinforcement(self, mock_ai_parse):
        """test_parse_incomplete_triggers_ai_reinforcement."""
        mock_ai_parse.return_value = MOCK_AI_RESPONSE_TRAVELPORT.copy()

        parser = TravelportParser()
        res = parser.parse(SAMPLE_TRAVELPORT_TICKET_INCOMPLETE)

        # Debería haber disparado la IA
        mock_ai_parse.assert_called_once()
        assert res.source_system == "TRAVELPORT"
        assert res.pnr == "ABC123"
        assert res.ticket_number == "1761234567890"
        assert res.passenger_name == "SMITH/JOHN"  # Regex no falló, se mantuvo original
        assert len(res.flights) == 1
        assert res.flights[0]["origen"] == "LIMA"
        assert res.flights[0]["destino"] == "CUZCO"
        assert res.flights[0]["numero_vuelo"] == "LA2415"
        assert res.fares.get("total_amount") == 350.0

    @patch("apps.automation.parsers.ai_universal_parser.UniversalAIParser.parse")
    def test_parse_ai_failure_fallback_to_regex(self, mock_ai_parse):
        """test_parse_ai_failure_fallback_to_regex."""
        # La IA lanza excepción, el parser debe devolver lo que extrajo la regex
        mock_ai_parse.side_effect = Exception("IA down")

        parser = TravelportParser()
        res = parser.parse(SAMPLE_TRAVELPORT_TICKET_INCOMPLETE)

        mock_ai_parse.assert_called_once()
        assert res.source_system == "TRAVELPORT"
        # Extraído con regex (aunque sean 'No encontrado')
        assert res.pnr == "No encontrado"
        assert res.ticket_number == "No encontrado"
        assert res.passenger_name == "SMITH/JOHN"

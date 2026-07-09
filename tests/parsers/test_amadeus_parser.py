from unittest.mock import patch

from apps.automation.parsers.base_parser import ParsedTicketData
from apps.automation.parsers.legacy.amadeus_parser import AmadeusParser

# Ticket Amadeus completo y bien formateado que puede parsear por Regex
SAMPLE_AMADEUS_TICKET_REGEX = """
ELECTRONIC TICKET RECEIPT
Booking ref: XYZ789
Ticket number: 176-1234567890
Traveler PEREZ/JUAN Agency
Date: 15 MAR 2026
ITINERARY
CARACAS ISTANBUL TK0224 U 15Mar 11:35 06:20
"""

# Ticket Amadeus incompleto que requiere AI reinforcement
SAMPLE_AMADEUS_TICKET_INCOMPLETE = """
ELECTRONIC TICKET RECEIPT
Booking ref: No encontrado
Ticket number: No encontrado
Traveler PEREZ/JUAN Agency
"""

MOCK_AI_RESPONSE_AMADEUS = {
    "CODIGO_RESERVA": "XYZ789",
    "NOMBRE_DEL_PASAJERO": "JUAN PEREZ",
    "NUMERO_DE_BOLETO": "1761234567890",
    "FECHA_DE_EMISION": "2026-03-15",
    "TARIFA_IMPORTE": 600.0,
    "TOTAL_IMPORTE": 650.0,
    "TOTAL_MONEDA": "USD",
    "itinerario": [
        {
            "aerolinea": "TK",
            "numero_vuelo": "TK0224",
            "origen": "CARACAS",
            "codigo_iata_origen": "CCS",
            "destino": "ISTANBUL",
            "codigo_iata_destino": "IST",
            "fecha_salida": "15Mar26",
            "hora_salida": "11:35",
            "hora_llegada": "06:20",
            "clase": "U",
        }
    ],
}


class TestAmadeusParser:
    def test_can_parse_valid_amadeus(self):
        parser = AmadeusParser()
        # Caso 1: CheckMyTrip
        assert parser.can_parse("Some text with CheckMyTrip inside") is True
        # Caso 2: AMADEUS
        assert parser.can_parse("AMADEUS GDS reservation details") is True
        # Caso 3: Electronic Ticket Receipt + Booking Ref
        assert parser.can_parse("ELECTRONIC TICKET RECEIPT\nBOOKING REF: ABC123") is True

    def test_can_parse_invalid_amadeus(self):
        parser = AmadeusParser()
        # Evitar colisión con KIUSYS
        assert parser.can_parse("KIUSYS SYSTEM ELECTRONIC TICKET RECEIPT BOOKING REF") is False
        # Texto random sin marcadores
        assert parser.can_parse("Random airline ticket layout") is False

    def test_parse_complete_regex(self):
        parser = AmadeusParser()
        res = parser.parse(SAMPLE_AMADEUS_TICKET_REGEX)

        assert isinstance(res, ParsedTicketData)
        assert res.source_system == "AMADEUS"
        assert res.pnr == "XYZ789"
        assert res.ticket_number == "1761234567890"
        assert res.passenger_name == "PEREZ/JUAN"
        assert len(res.flights) == 1
        assert res.flights[0]["origen"] == "CARACAS"
        assert res.flights[0]["destino"] == "ISTANBUL"
        assert res.flights[0]["numero_vuelo"] == "TK0224"

    @patch("apps.automation.parsers.ai_universal_parser.UniversalAIParser.parse")
    def test_parse_incomplete_triggers_ai_reinforcement(self, mock_ai_parse):
        mock_ai_parse.return_value = MOCK_AI_RESPONSE_AMADEUS.copy()

        parser = AmadeusParser()
        res = parser.parse(SAMPLE_AMADEUS_TICKET_INCOMPLETE)

        # Debería haber disparado la IA
        mock_ai_parse.assert_called_once()
        assert res.source_system == "AMADEUS"
        assert res.pnr == "XYZ789"
        assert res.ticket_number == "1761234567890"
        assert res.passenger_name == "PEREZ/JUAN"  # Regex no falló, se mantuvo original
        assert len(res.flights) == 1
        assert res.flights[0]["origen"] == "CARACAS"
        assert res.flights[0]["destino"] == "ISTANBUL"
        assert res.flights[0]["numero_vuelo"] == "TK0224"
        assert res.fares.get("total_amount") == 650.0

    @patch("apps.automation.parsers.ai_universal_parser.UniversalAIParser.parse")
    def test_parse_ai_failure_fallback_to_regex(self, mock_ai_parse):
        # La IA lanza excepción, el parser debe devolver lo que extrajo la regex
        mock_ai_parse.side_effect = Exception("IA down")

        parser = AmadeusParser()
        res = parser.parse(SAMPLE_AMADEUS_TICKET_INCOMPLETE)

        mock_ai_parse.assert_called_once()
        assert res.source_system == "AMADEUS"
        # Extraído con regex (aunque sean 'No encontrado')
        assert res.pnr == "No encontrado"
        assert res.ticket_number == "No encontrado"
        assert res.passenger_name == "PEREZ/JUAN"  # Extraído por regex Traveler PEREZ/JUAN Agency

    @patch("apps.automation.parsers.ai_universal_parser.UniversalAIParser.parse")
    def test_parse_empty_itinerary_triggers_ai_reinforcement(self, mock_ai_parse):
        # Un ticket con datos básicos por regex pero sin itinerario
        TICKET_NO_FLIGHTS = """
        ELECTRONIC TICKET RECEIPT
        Booking ref: XYZ789
        Ticket number: 176-1234567890
        Traveler PEREZ/JUAN Agency
        Date: 15 MAR 2026
        """
        mock_ai_parse.return_value = MOCK_AI_RESPONSE_AMADEUS.copy()

        parser = AmadeusParser()
        res = parser.parse(TICKET_NO_FLIGHTS)

        # Debería haber disparado la IA porque no se encontraron vuelos por regex
        mock_ai_parse.assert_called_once()
        assert res.source_system == "AMADEUS"
        assert res.pnr == "XYZ789"
        assert len(res.flights) == 1
        assert res.flights[0]["numero_vuelo"] == "TK0224"

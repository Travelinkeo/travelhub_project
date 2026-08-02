"""Tests para KIU Parser - crítico para costos IA."""

import pytest

from apps.automation.parsers.base_parser import ParsedTicketData
from apps.automation.parsers.kiu_parser import KIUParser


@pytest.fixture
def kiu_parser():
    return KIUParser()


class TestKIUParserDetection:
    """Tests de detección de formato KIU."""

    def test_can_parse_kiusys_com(self, kiu_parser):
        text = "KIUSYS.COM\nPASSENGER ITINERARY RECEIPT"
        assert kiu_parser.can_parse(text) is True

    def test_can_parse_passenger_itinerary(self, kiu_parser):
        text = "PASSENGER ITINERARY RECEIPT\nISSUE AGENT/AGENTE EMISOR"
        assert kiu_parser.can_parse(text) is True

    def test_can_parse_issue_agent(self, kiu_parser):
        text = "ISSUE AGENT/AGENTE EMISOR\nFROM/TO"
        assert kiu_parser.can_parse(text) is True

    def test_rejects_non_kiu(self, kiu_parser):
        text = "SABRE RECEIPT\nPNR ABC123"
        assert kiu_parser.can_parse(text) is False


class TestKIUParserPNRExtraction:
    """Tests de extracción de PNR en KIU."""

    def test_extract_pnr_from_kiusys(self, kiu_parser):
        text = "KIUSYS.COM\nPNR ABC123"
        result = kiu_parser._extract_pnr(text)
        assert result == "ABC123"

    def test_extract_pnr_from_reserva(self, kiu_parser):
        text = "RESERVA: DEF456\nPNR: DEF456"
        result = kiu_parser._extract_pnr(text)
        assert result == "DEF456"

    def test_pnr_not_found(self, kiu_parser):
        text = "NO PNR HERE"
        result = kiu_parser._extract_pnr(text)
        assert result == "No encontrado"


class TestKIUParserTicketNumber:
    """Tests de extracción de número de boleto."""

    def test_extract_ticket_13_digits(self, kiu_parser):
        text = "TICKET: 1234567890123"
        result = kiu_parser._extract_ticket_number(text)
        assert result == "1234567890123"

    def test_extract_ticket_10_digits_with_prefix(self, kiu_parser):
        text = "TKT: 1234567890"
        result = kiu_parser._extract_ticket_number(text)
        assert result == "2351234567890"  # Adds 235 prefix

    def test_ticket_not_found(self, kiu_parser):
        text = "NO TICKET"
        result = kiu_parser._extract_ticket_number(text)
        assert result == "No encontrado"


class TestKIUParserPassengerName:
    """Tests de extracción de nombre de pasajero."""

    def test_extract_name_standard(self, kiu_parser):
        text = "PASSENGER NAME: PEREZ/JUAN MR"
        result = kiu_parser._extract_passenger_name(text)
        assert "PEREZ/JUAN" in result

    def test_clean_name_removes_titles(self, kiu_parser):
        name = "PEREZ/JUAN MR"
        result = kiu_parser.clean_passenger_name(name)
        assert "MR" not in result
        assert "PEREZ/JUAN" in result


class TestKIUFlightExtraction:
    """Tests de extracción de vuelos KIU."""

    def test_extract_flight_sabre_format(self, kiu_parser):
        text = "1 AV 46 C 22MAY BOGMAD HK1 0700 2330"
        parsed = kiu_parser._parse_raw_kiu_lines(text)
        assert len(parsed.flights) == 1
        flight = parsed.flights[0]
        assert flight["aerolinea"] == "AV"
        assert flight["numero_vuelo"] == "46"
        assert flight["fecha_salida"] == "22MAY"
        assert flight["origen"] == "BOG"
        assert flight["destino"] == "MAD"
        assert flight["hora_salida"] == "07:00"
        assert flight["hora_llegada"] == "23:30"

    def test_empty_flights(self, kiu_parser):
        text = "NO FLIGHTS HERE"
        flights = kiu_parser._extract_flights(text, "")
        assert flights == []


class TestKIUParserAmounts:
    """Tests de extracción de montos y detección de reemisión."""

    def test_detect_remission(self, kiu_parser):
        text = "TOTAL: 1000\nNETO: 1200"
        amounts = kiu_parser._extract_amounts(text)
        assert amounts["es_remision"] is True

    def test_no_remission(self, kiu_parser):
        text = "TOTAL: 1000\nNETO: 1000"
        amounts = kiu_parser._extract_amounts(text)
        assert amounts["es_remision"] is False


class TestKIUParserEdgeCases:
    """Tests de casos borde."""

    def test_empty_text(self, kiu_parser):
        result = kiu_parser.parse("")
        assert isinstance(result, ParsedTicketData)
        assert result.pnr == "No encontrado"

    def test_none_text(self, kiu_parser):
        result = kiu_parser.parse(None)
        assert isinstance(result, ParsedTicketData)
        assert result.pnr == "No encontrado"

    def test_html_stripping(self, kiu_parser):
        text = "<html><body>PNR ABC123</body></html>"
        result = kiu_parser._extract_pnr(text)
        assert result == "ABC123"

    def test_name_with_boleto_nro(self, kiu_parser):
        name = "BOLETO NRO 123"
        result = kiu_parser._extract_passenger_name(name)
        assert "BOLETO NRO" in result or "PENDIENTE" in result


class TestKIUParserFullIntegration:
    """Test de integración completa con muestras reales."""

    def test_parse_complete_kiu_ticket(self, kiu_parser):
        sample = """
        KIUSYS.COM
        PASSENGER ITINERARY RECEIPT
        PNR: ABC123
        PASSENGER NAME: PEREZ/JUAN MR
        TICKET: 1234567890123
        ISSUE DATE: 15JAN26
        TOTAL: USD 1000.00
        """
        result = kiu_parser.parse(sample)
        assert isinstance(result, ParsedTicketData)
        assert result.pnr == "ABC123"
        assert "PEREZ/JUAN" in result.passenger_name
        assert result.ticket_number == "1234567890123"
        assert result.source_system == "KIU"

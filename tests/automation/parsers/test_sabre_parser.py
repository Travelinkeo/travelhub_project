"""Tests para Sabre Parser."""

import pytest

from apps.automation.parsers.base_parser import ParsedTicketData
from apps.automation.parsers.legacy.sabre_parser import SabreParser


@pytest.fixture
def sabre_parser():
    return SabreParser()


class TestSabreParserDetection:
    def test_can_parse_sabre(self, sabre_parser):
        text = "SABRE ELECTRONIC TICKET RECEIPT\nRESERVATION CODE ABC123\nPASSENGER: PEREZ/JUAN"
        assert sabre_parser.can_parse(text) is True

    def test_can_parse_sabre_recibo(self, sabre_parser):
        text = "RECIBO DE PASAJE SABRE\nCÓDIGO DE RESERVACIÓN ABC123\nPASAJERO PEREZ/JUAN"
        assert sabre_parser.can_parse(text) is True

    def test_rejects_non_sabre(self, sabre_parser):
        text = "AMADEUS RECEIPT\nPNR ABC123"
        assert sabre_parser.can_parse(text) is False

    def test_rejects_kiu(self, sabre_parser):
        text = "KIUSYS.COM\nPASSENGER ITINERARY RECEIPT"
        assert sabre_parser.can_parse(text) is False


class TestSabreParserFields:
    def test_extract_pnr(self, sabre_parser):
        text = "RESERVATION CODE: ABC123\nPASSENGER: PEREZ/JUAN"
        result = sabre_parser.extract_field(
            text, [r"(?:Reservation Code|C[OÓ]DIGO DE RESERVA(?:CI[OÓ]N)?)\s*[:\t\s]*([A-Z0-9]{6})"]
        )
        assert result == "ABC123"

    def test_extract_passenger_name(self, sabre_parser):
        text = "Preparado para PEREZ/JUAN [200687]\nRESERVATION CODE: ABC123"
        result = sabre_parser.extract_passenger_name_robust(text)
        assert "PEREZ/JUAN" in result


class TestSabreParserEdgeCases:
    def test_empty_text_returns_dto(self, sabre_parser):
        result = sabre_parser.parse("")
        assert isinstance(result, ParsedTicketData)

"""Tests para Amadeus Parser."""

import pytest

from apps.automation.parsers.amadeus_parser import AmadeusParser
from apps.automation.parsers.base_parser import ParsedTicketData


@pytest.fixture
def amadeus_parser():
    return AmadeusParser()


class TestAmadeusParserDetection:
    def test_can_parse_amadeus(self, amadeus_parser):
        text = "AMADEUS ELECTRONIC TICKET RECEIPT\nBOOKING REF ABC123"
        assert amadeus_parser.can_parse(text) is True

    def test_can_parse_checkmytrip(self, amadeus_parser):
        text = "CHECKMYTRIP ELECTRONIC TICKET RECEIPT\nBOOKING REF ABC123"
        assert amadeus_parser.can_parse(text) is True

    def test_rejects_non_amadeus(self, amadeus_parser):
        text = "SABRE RECEIPT\nPNR ABC123"
        assert amadeus_parser.can_parse(text) is False


class TestAmadeusParserFields:
    def test_extract_pnr(self, amadeus_parser):
        text = "Booking ref: ABC123\nPASSENGER: PEREZ/JUAN"
        result = amadeus_parser.extract_field(
            text,
            [
                r"Booking ref\s*?:\s*([A-Z0-9]{6})",
                r"Booking reference\s*?:\s*([A-Z0-9]{6})",
            ],
        )
        assert result == "ABC123"


class TestAmadeusParserEdgeCases:
    def test_empty_text_returns_dto(self, amadeus_parser):
        result = amadeus_parser.parse("")
        assert isinstance(result, ParsedTicketData)

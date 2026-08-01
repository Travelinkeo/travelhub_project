"""Tests para Amadeus Parser."""

import pytest

from apps.automation.parsers.legacy.amadeus_parser import AmadeusParser


@pytest.fixture
def amadeus_parser():
    return AmadeusParser()


class TestAmadeusParserDetection:
    def test_can_parse_amadeus(self, amadeus_parser):
        text = "AMADEUS RECEIPT\nPNR: ABC123"
        assert amadeus_parser.can_parse(text) is True

    def test_can_parse_amadeus_ticket(self, amadeus_parser):
        text = "AMADEUS TICKET\nPNR ABC123"
        assert amadeus_parser.can_parse(text) is True

    def test_rejects_non_amadeus(self, amadeus_parser):
        text = "SABRE RECEIPT\nPNR ABC123"
        assert amadeus_parser.can_parse(text) is False


class TestAmadeusParserPNR:
    def test_extract_pnr(self, amadeus_parser):
        text = "PNR: ABC123\nRESERVATION CODE DEF456"
        result = amadeus_parser._extract_pnr(text)
        assert result == "ABC123"


class TestAmadeusParserEdgeCases:
    def test_empty_text(self, amadeus_parser):
        result = amadeus_parser.parse("")
        assert "error" in result

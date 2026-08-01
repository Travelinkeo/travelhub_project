"""Tests para Travelport Parser."""

import pytest

from apps.automation.parsers.legacy.travelport_parser import TravelportParser


@pytest.fixture
def travelport_parser():
    return TravelportParser()


class TestTravelportParserDetection:
    def test_can_parse_travelport(self, travelport_parser):
        text = "TRAVELPORT RECEIPT\nPNR: ABC123"
        assert travelport_parser.can_parse(text) is True

    def test_can_parse_1p_code(self, travelport_parser):
        text = "1PTRAVELPORT\nPNR ABC123"
        assert travelport_parser.can_parse(text) is True

    def test_rejects_non_travelport(self, travelport_parser):
        text = "SABRE RECEIPT\nPNR ABC123"
        assert travelport_parser.can_parse(text) is False


class TestTravelportParserPNR:
    def test_extract_pnr(self, travelport_parser):
        text = "PNR: ABC123\nRESERVATION CODE DEF456"
        result = travelport_parser._extract_pnr(text)
        assert result == "ABC123"


class TestTravelportParserEdgeCases:
    def test_empty_text(self, travelport_parser):
        result = travelport_parser.parse("")
        assert "error" in result

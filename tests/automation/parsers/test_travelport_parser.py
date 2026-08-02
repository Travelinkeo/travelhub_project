"""Tests para Travelport Parser."""

import pytest

from apps.automation.parsers.base_parser import ParsedTicketData
from apps.automation.parsers.legacy.travelport_parser import TravelportParser


@pytest.fixture
def travelport_parser():
    return TravelportParser()


class TestTravelportParserDetection:
    def test_can_parse_travelport(self, travelport_parser):
        text = "TRAVELPORT ELECTRONIC TICKET RECEIPT\nBOOKING REFERENCE ABC123"
        assert travelport_parser.can_parse(text) is True

    def test_can_parse_galileo(self, travelport_parser):
        text = "GALILEO ELECTRONIC TICKET RECEIPT\nBOOKING REFERENCE ABC123"
        assert travelport_parser.can_parse(text) is True

    def test_rejects_non_travelport(self, travelport_parser):
        text = "SABRE RECEIPT\nPNR ABC123"
        assert travelport_parser.can_parse(text) is False


class TestTravelportParserFields:
    def test_extract_pnr(self, travelport_parser):
        text = "BOOKING REFERENCE: ABC123\nPASSENGER: PEREZ/JUAN"
        result = travelport_parser.extract_field(
            text,
            [
                r"BOOKING REFERENCE\s*[:\s]*([A-Z0-9]{6})",
                r"RESERVATION CODE\s*[:\s]*([A-Z0-9]{6})",
            ],
        )
        assert result == "ABC123"


class TestTravelportParserEdgeCases:
    def test_empty_text_returns_dto(self, travelport_parser):
        result = travelport_parser.parse("")
        assert isinstance(result, ParsedTicketData)

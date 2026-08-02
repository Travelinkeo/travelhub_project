"""Tests para Wingo Parser."""

import pytest

from apps.automation.parsers.base_parser import ParsedTicketData
from apps.automation.parsers.legacy.wingo_parser import WingoParser


@pytest.fixture
def wingo_parser():
    return WingoParser()


class TestWingoParserDetection:
    def test_can_parse_wingo(self, wingo_parser):
        text = "WINGO\nCódigo de reserva ABC123"
        assert wingo_parser.can_parse(text) is True

    def test_can_parse_wingo_com(self, wingo_parser):
        text = "WINGO.COM\nCódigo de reserva ABC123"
        assert wingo_parser.can_parse(text) is True

    def test_rejects_non_wingo(self, wingo_parser):
        text = "SABRE RECEIPT\nPNR ABC123"
        assert wingo_parser.can_parse(text) is False


class TestWingoParserFields:
    def test_extract_pnr(self, wingo_parser):
        text = "Código de reserva ABC123\nWINGO"
        result = wingo_parser.extract_field(
            text, [r"(?:C[óo]digo de reserva|reserva)\s+([A-Z0-9]{6})"]
        )
        assert result == "ABC123"


class TestWingoParserEdgeCases:
    def test_empty_text_returns_dto(self, wingo_parser):
        result = wingo_parser.parse("")
        assert isinstance(result, ParsedTicketData)

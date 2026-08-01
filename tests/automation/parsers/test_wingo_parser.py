"""Tests para Wingo Parser."""

import pytest

from apps.automation.parsers.legacy.wingo_parser import WingoParser


@pytest.fixture
def wingo_parser():
    return WingoParser()


class TestWingoParserDetection:
    def test_can_parse_wingo(self, wingo_parser):
        text = "WINGO AIRLINES\nPNR: ABC123"
        assert wingo_parser.can_parse(text) is True

    def test_rejects_non_wingo(self, wingo_parser):
        text = "SABRE RECEIPT\nPNR ABC123"
        assert wingo_parser.can_parse(text) is False


class TestWingoParserPNR:
    def test_extract_pnr(self, wingo_parser):
        text = "PNR: ABC123\nRESERVATION CODE DEF456"
        result = wingo_parser._extract_pnr(text)
        assert result == "ABC123"


class TestWingoParserEdgeCases:
    def test_empty_text(self, wingo_parser):
        result = wingo_parser.parse("")
        assert "error" in result

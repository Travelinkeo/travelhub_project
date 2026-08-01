"""Tests para TK Connect Parser."""

import pytest

from apps.automation.parsers.legacy.tk_connect_parser import TKConnectParser


@pytest.fixture
def tk_parser():
    return TKConnectParser()


class TestTKConnectParserDetection:
    def test_can_parse_tkconnect(self, tk_parser):
        text = "TKCONNECT\nPNR: ABC123"
        assert tk_parser.can_parse(text) is True

    def test_can_parse_tk_code(self, tk_parser):
        text = "1TTKCONNECT\nPNR ABC123"
        assert tk_parser.can_parse(text) is True

    def test_rejects_non_tk(self, tk_parser):
        text = "SABRE RECEIPT\nPNR ABC123"
        assert tk_parser.can_parse(text) is False


class TestTKConnectParserPNR:
    def test_extract_pnr(self, tk_parser):
        text = "PNR: ABC123\nTK RESERVATION DEF456"
        result = tk_parser._extract_pnr(text)
        assert result == "ABC123"


class TestTKConnectParserEdgeCases:
    def test_empty_text(self, tk_parser):
        result = tk_parser.parse("")
        assert "error" in result

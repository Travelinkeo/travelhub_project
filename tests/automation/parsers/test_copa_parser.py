"""Tests para Copa Parser."""

import pytest

from apps.automation.parsers.legacy.copa_parser import CopaParser


@pytest.fixture
def copa_parser():
    return CopaParser()


class TestCopaParserDetection:
    def test_can_parse_copa(self, copa_parser):
        text = "COPA AIRLINES\nPNR: ABC123"
        assert copa_parser.can_parse(text) is True

    def test_rejects_non_copa(self, copa_parser):
        text = "SABRE RECEIPT\nPNR ABC123"
        assert copa_parser.can_parse(text) is False


class TestCopaParserPNR:
    def test_extract_pnr(self, copa_parser):
        text = "PNR: ABC123\nRESERVATION CODE DEF456"
        result = copa_parser._extract_pnr(text)
        assert result == "ABC123"


class TestCopaParserEdgeCases:
    def test_empty_text(self, copa_parser):
        result = copa_parser.parse("")
        assert "error" in result

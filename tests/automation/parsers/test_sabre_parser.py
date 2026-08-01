"""Tests para Sabre Parser."""

import pytest

from apps.automation.parsers.legacy.sabre_parser import SabreParser


@pytest.fixture
def sabre_parser():
    return SabreParser()


class TestSabreParserDetection:
    def test_can_parse_sabre(self, sabre_parser):
        text = "SABRE RECEIPT\nPNR: ABC123"
        assert sabre_parser.can_parse(text) is True

    def test_can_parse_sabre_recibo(self, sabre_parser):
        text = "RECIBO DE PASAJE SABRE\nPNR ABC123"
        assert sabre_parser.can_parse(text) is True

    def test_rejects_non_sabre(self, sabre_parser):
        text = "AMADEUS RECEIPT\nPNR ABC123"
        assert sabre_parser.can_parse(text) is False


class TestSabreParserPNR:
    def test_extract_pnr(self, sabre_parser):
        text = "PNR: ABC123\nRESERVATION CODE DEF456"
        result = sabre_parser._extract_pnr(text)
        assert result == "ABC123"


class TestSabreParserEdgeCases:
    def test_empty_text(self, sabre_parser):
        result = sabre_parser.parse("")
        assert "error" in result

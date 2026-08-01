"""Tests para Web Receipt Parser."""

import pytest

from apps.automation.parsers.legacy.web_receipt_parser import WebReceiptParser


@pytest.fixture
def web_receipt_parser():
    return WebReceiptParser()


class TestWebReceiptParserDetection:
    def test_can_parse_web_receipt(self, web_receipt_parser):
        text = "WEB RECEIPT\nPNR: ABC123"
        assert web_receipt_parser.can_parse(text) is True

    def test_rejects_non_web_receipt(self, web_receipt_parser):
        text = "SABRE RECEIPT\nPNR ABC123"
        assert web_receipt_parser.can_parse(text) is False


class TestWebReceiptParserPNR:
    def test_extract_pnr(self, web_receipt_parser):
        text = "PNR: ABC123\nCONFIRMATION DEF456"
        result = web_receipt_parser._extract_pnr(text)
        assert result == "ABC123"


class TestWebReceiptParserEdgeCases:
    def test_empty_text(self, web_receipt_parser):
        result = web_receipt_parser.parse("")
        assert "error" in result

"""Tests para Web Receipt Parser."""

import pytest

from apps.automation.parsers.legacy.web_receipt_parser import WebReceiptParser


@pytest.fixture
def web_receipt_parser():
    return WebReceiptParser()


class TestWebReceiptParserDetection:
    def test_can_parse_avior(self, web_receipt_parser):
        text = "AVIOR AIRLINES\nLOCALIZADOR ABC123\nRESERVA"
        assert web_receipt_parser.can_parse(text) is True

    def test_can_parse_rutaca(self, web_receipt_parser):
        text = "TICKETS RUTACA\nLOCALIZADOR ABC123"
        assert web_receipt_parser.can_parse(text) is True

    def test_can_parse_estelar(self, web_receipt_parser):
        text = "ESTELAR TICKETS ESTELAR\nLOCALIZADOR ABC123"
        assert web_receipt_parser.can_parse(text) is True

    def test_rejects_non_web_receipt(self, web_receipt_parser):
        text = "SABRE RECEIPT\nPNR ABC123"
        assert web_receipt_parser.can_parse(text) is False


class TestWebReceiptParserEdgeCases:
    def test_empty_text_no_crash(self, web_receipt_parser):
        # parse("") retorna None legítimamente (no hay nada que parsear)
        result = web_receipt_parser.parse("")
        assert result is None

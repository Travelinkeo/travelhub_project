"""Tests para TK Connect Parser."""

import pytest

from apps.automation.parsers.base_parser import ParsedTicketData
from apps.automation.parsers.legacy.tk_connect_parser import TKConnectParser


@pytest.fixture
def tk_parser():
    return TKConnectParser()


class TestTKConnectParserDetection:
    def test_can_parse_tkconnect(self, tk_parser):
        text = "IDENTIFICACIÓN DEL PEDIDO\nTK CONNECT"
        assert tk_parser.can_parse(text) is True

    def test_can_parse_turkish(self, tk_parser):
        text = "IDENTIFICACIÓN DEL PEDIDO\nTURKISH AIRLINES"
        assert tk_parser.can_parse(text) is True

    def test_rejects_non_tk(self, tk_parser):
        text = "SABRE RECEIPT\nPNR ABC123"
        assert tk_parser.can_parse(text) is False


class TestTKConnectParserFields:
    def test_extract_pnr(self, tk_parser):
        result = tk_parser.parse(
            "IDENTIFICACIÓN DEL PEDIDO\nTK CONNECT\nCÓDIGO DE RESERVACIÓN ABC123"
        )
        assert isinstance(result, ParsedTicketData)


class TestTKConnectParserEdgeCases:
    def test_empty_text_returns_dto(self, tk_parser):
        result = tk_parser.parse("")
        assert isinstance(result, ParsedTicketData)

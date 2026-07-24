"""Tests para el módulo de parsers GDS — base_parser, registry, ticket_parser."""

import unittest.mock
from decimal import Decimal

import pytest

from apps.automation.parsers.base_parser import BaseTicketParser, ParsedTicketData
from apps.automation.parsers.registry import ParserRegistry

pytestmark = [pytest.mark.unit]


# ─── ParsedTicketData ──────────────────────────────────────────────


class TestParsedTicketData:
    def test_default_construction(self):
        data = ParsedTicketData(
            source_system="TEST",
            pnr="ABC123",
            ticket_number="1234567890",
            passenger_name="TEST/PASSENGER",
            issue_date="01JAN26",
        )
        assert data.source_system == "TEST"
        assert data.pnr == "ABC123"
        assert data.es_remision is False
        assert data.flights == []
        assert data.fares == {}

    def test_post_init_converts_list_fares_to_dict(self):
        data = ParsedTicketData(
            source_system="TEST",
            pnr="ABC123",
            ticket_number="1234567890",
            passenger_name="TEST",
            issue_date="01JAN26",
            fares=[100.0, 20.0, 120.0],
        )
        assert isinstance(data.fares, dict)
        assert data.fares["total_amount"] == 120.0
        assert data.fares["tax_amount"] == 20.0
        assert data.fares["fare_amount"] == 100.0

    def test_post_init_keeps_dict_fares(self):
        data = ParsedTicketData(
            source_system="TEST",
            pnr="ABC123",
            ticket_number="1234567890",
            passenger_name="TEST",
            issue_date="01JAN26",
            fares={"total_amount": 500, "custom_key": "val"},
        )
        assert data.fares["total_amount"] == 500
        assert data.fares["custom_key"] == "val"

    def test_to_dict_includes_required_keys(self):
        data = ParsedTicketData(
            source_system="KIU",
            pnr="DEF456",
            ticket_number="0987654321",
            passenger_name="GARCIA/MARIA",
            issue_date="15JAN26",
        )
        result = data.to_dict()
        assert result["SOURCE_SYSTEM"] == "KIU"
        assert result["codigo_reservacion"] == "DEF456"
        assert result["numero_boleto"] == "0987654321"

    def test_to_pydantic_validates(self):
        data = ParsedTicketData(
            source_system="KIU",
            pnr="GHI789",
            ticket_number="1112223334445",
            passenger_name="PEREZ/JUAN",
            issue_date="20JAN26",
        )
        schema = data.to_pydantic()
        assert schema is not None
        assert len(schema.boletos) == 1
        boleto = schema.boletos[0]
        assert boleto.codigo_reserva == "GHI789"


# ─── BaseTicketParser utilities ────────────────────────────────────


class TestBaseTicketParser:
    class ConcreteParser(BaseTicketParser):
        def can_parse(self, text: str) -> bool:
            return "TEST" in text

        def parse(self, text: str, html_text: str = "") -> ParsedTicketData:
            return ParsedTicketData(
                source_system="TEST",
                pnr="PARSED",
                ticket_number="0000000000",
                passenger_name="PARSED/NAME",
                issue_date="01JAN26",
            )

    def test_cannot_instantiate_abstract(self):
        with pytest.raises(TypeError):
            BaseTicketParser()

    def test_concrete_parser(self):
        parser = self.ConcreteParser()
        assert parser.can_parse("this is a TEST ticket") is True
        assert parser.can_parse("no match") is False

    def test_clean_text(self):
        parser = self.ConcreteParser()
        result = parser.clean_text("  lots   of   spaces  ")
        assert result == "lots of spaces"

    def test_purify_text_for_detection(self):
        parser = self.ConcreteParser()
        result = parser.purify_text_for_detection("<html><b>KIU</b> Ticket</html>")
        assert "KIU" in result
        assert "<html>" not in result

    def test_extract_field_finds_first_pattern(self):
        parser = self.ConcreteParser()
        text = "PASSENGER NAME: JUAREZ/RAUL\nPASSENGER: OTRO"
        result = parser.extract_field(text, [r"PASSENGER NAME:\s*(.+)", r"PASSENGER:\s*(.+)"])
        assert result == "JUAREZ/RAUL"

    def test_extract_field_returns_default_on_no_match(self):
        parser = self.ConcreteParser()
        result = parser.extract_field(
            "no relevant data", [r"MISSING:\s*(.+)"], default="NOT FOUND"
        )
        assert result == "NOT FOUND"

    def test_extract_field_negative_lookahead(self):
        parser = self.ConcreteParser()
        text = "AGENT: SYSTEM AUTO"
        result = parser.extract_field(
            text,
            [r"AGENT:\s*(.+)"],
            negative_lookahead_patterns=[r"SYSTEM"],
        )
        assert result == "No encontrado"

    def test_extract_currency_amount_usd(self):
        parser = self.ConcreteParser()
        cur, amt = parser.extract_currency_amount("USD 1,234.56")
        assert cur == "USD"
        assert amt == Decimal("1234.56")

    def test_extract_currency_amount_none(self):
        parser = self.ConcreteParser()
        cur, amt = parser.extract_currency_amount("no currency here")
        assert cur is None
        assert amt is None

    def test_clean_passenger_name_removes_title(self):
        parser = self.ConcreteParser()
        result = parser.clean_passenger_name("JUAREZ/RAUL MR")
        assert "MR" not in result
        assert "JUAREZ/RAUL" in result

    def test_normalize_airline_name(self, monkeypatch):
        mock_normalize = unittest.mock.MagicMock(return_value="Avianca")
        monkeypatch.setattr(
            "apps.automation.parsers.base_parser.normalize_airline_name",
            mock_normalize,
        )
        parser = self.ConcreteParser()
        result = parser.normalize_airline_name("AVIANCA")
        assert result == "Avianca"

    def test_extract_passenger_name_robust(self):
        parser = self.ConcreteParser()
        result = parser.extract_passenger_name_robust(
            "PASSENGER NAME: PEREZ/JUAN\nOTHER DATA"
        )
        assert "PEREZ/JUAN" in result


# ─── ParserRegistry ────────────────────────────────────────────────


class TestParserRegistry:
    def setup_method(self):
        self.reg = ParserRegistry()

    def test_register_and_find_parser(self):
        from tests.services.test_parsers import TestBaseTicketParser

        parser = TestBaseTicketParser.ConcreteParser()
        self.reg.register(parser)
        found = self.reg.find_parser("this is a TEST")
        assert found is parser

    def test_find_parser_returns_none_when_no_match(self):
        parser = TestBaseTicketParser.ConcreteParser()
        self.reg.register(parser)
        found = self.reg.find_parser("no match here")
        assert found is None

    def test_get_all_parsers(self):
        from tests.services.test_parsers import TestBaseTicketParser

        self.reg.register(TestBaseTicketParser.ConcreteParser())
        assert len(self.reg.get_all_parsers()) == 1

    def test_clear(self):
        from tests.services.test_parsers import TestBaseTicketParser

        self.reg.register(TestBaseTicketParser.ConcreteParser())
        self.reg.clear()
        assert len(self.reg.get_all_parsers()) == 0

    def test_register_raises_type_error(self):
        with pytest.raises(TypeError):
            self.reg.register("not a parser")  # type: ignore

    def test_registry_singleton(self):
        from apps.automation.parsers.registry import registry as r1
        from apps.automation.parsers.registry import registry as r2

        assert r1 is r2


# ─── FastDeterministicParsers ──────────────────────────────────────


class TestFastDeterministicParsers:
    @pytest.mark.skip(reason="Requiere texto de boleto real para probar regex complejos")
    def test_parse_general_regex_basic(self):
        from apps.automation.parsers.ticket_parser import FastDeterministicParsers

        text = """
        PASSENGER: DOE/JOHN
        TICKET: 1234567890123
        """
        result = FastDeterministicParsers.parse_general_regex(text)
        assert isinstance(result, dict)


# ─── is_brand_color_dark ──────────────────────────────────────────


class TestIsBrandColorDark:
    def test_dark_color(self):
        from apps.automation.parsers.ticket_parser import is_brand_color_dark

        assert is_brand_color_dark("#000000") is True
        assert is_brand_color_dark("#0a0a0a") is True

    def test_light_color(self):
        from apps.automation.parsers.ticket_parser import is_brand_color_dark

        assert is_brand_color_dark("#FFFFFF") is False
        assert is_brand_color_dark("#f0f0f0") is False

    def test_invalid_color_defaults_true(self):
        from apps.automation.parsers.ticket_parser import is_brand_color_dark

        assert is_brand_color_dark("invalid") is True


# ─── _apply_universal_schema_filter ────────────────────────────────


class TestApplyUniversalSchemaFilter:
    def test_passes_through_data(self):
        from apps.automation.parsers.ai_universal_parser import _apply_universal_schema_filter

        data = {"key": "value", "other": 123}
        result = _apply_universal_schema_filter(data)
        assert result == data

    def test_handles_empty_dict(self):
        from apps.automation.parsers.ai_universal_parser import _apply_universal_schema_filter

        assert _apply_universal_schema_filter({}) == {}

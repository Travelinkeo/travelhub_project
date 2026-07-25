"""Tests para ParserRegistry"""

from apps.automation.parsers.legacy.amadeus_parser import AmadeusParser
from apps.automation.parsers.legacy.sabre_parser import SabreParser
from apps.automation.parsers.registry import ParserRegistry


class TestParserRegistry:
    """Tests para registro de parsers"""

    def test_register_parser(self):
        """Register parser."""
        registry = ParserRegistry()
        parser = SabreParser()
        registry.register(parser)
        assert len(registry.get_all_parsers()) == 1

    def test_find_parser_sabre(self):
        """Find parser sabre."""
        registry = ParserRegistry()
        registry.register(SabreParser())

        text = "ETICKET RECEIPT\nRESERVATION CODE: ABC123"
        parser = registry.find_parser(text)
        assert parser is not None
        assert isinstance(parser, SabreParser)

    def test_find_parser_amadeus(self):
        """Find parser amadeus."""
        registry = ParserRegistry()
        registry.register(AmadeusParser())

        text = "ELECTRONIC TICKET RECEIPT\nBOOKING REF: XYZ789"
        parser = registry.find_parser(text)
        assert parser is not None
        assert isinstance(parser, AmadeusParser)

    def test_find_parser_no_match(self):
        """Find parser no match."""
        registry = ParserRegistry()
        registry.register(SabreParser())

        text = "Random text without markers"
        parser = registry.find_parser(text)
        assert parser is None

    def test_clear_registry(self):
        """Clear registry."""
        registry = ParserRegistry()
        registry.register(SabreParser())
        registry.register(AmadeusParser())
        assert len(registry.get_all_parsers()) == 2

        registry.clear()
        assert len(registry.get_all_parsers()) == 0

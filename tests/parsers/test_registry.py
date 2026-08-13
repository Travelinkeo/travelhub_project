from apps.automation.parsers.amadeus_parser import AmadeusParser
from apps.automation.parsers.kiu_parser import KIUParser
from apps.automation.parsers.registry import ParserRegistry


class TestParserRegistry:
    """Tests para registro de parsers"""

    def test_register_parser(self):
        """test_register_parser."""
        registry = ParserRegistry()
        parser = KIUParser()
        registry.register(parser)
        assert len(registry.get_all_parsers()) == 1

    def test_find_parser_kiu(self):
        """test_find_parser_kiu."""
        registry = ParserRegistry()
        registry.register(KIUParser())

        text = "KIUSYS.COM ITINERARY RECEIPT"
        parser = registry.find_parser(text)
        assert parser is not None
        assert isinstance(parser, KIUParser)

    def test_find_parser_amadeus(self):
        """test_find_parser_amadeus."""
        registry = ParserRegistry()
        registry.register(AmadeusParser())

        text = "ELECTRONIC TICKET RECEIPT\nBOOKING REF: XYZ789"
        parser = registry.find_parser(text)
        assert parser is not None
        assert isinstance(parser, AmadeusParser)

    def test_find_parser_no_match(self):
        """test_find_parser_no_match."""
        registry = ParserRegistry()
        registry.register(KIUParser())

        text = "Random text without markers"
        parser = registry.find_parser(text)
        assert parser is None

    def test_clear_registry(self):
        """test_clear_registry."""
        registry = ParserRegistry()
        registry.register(KIUParser())
        registry.register(AmadeusParser())
        assert len(registry.get_all_parsers()) == 2

        registry.clear()
        assert len(registry.get_all_parsers()) == 0

"""Tests adicionales para aumentar cobertura de parsers"""

from apps.automation.parsers.kiu_parser import KIUParser
from apps.automation.parsers.legacy.amadeus_parser import AmadeusParser
from apps.automation.parsers.legacy.sabre_parser import SabreParser


class TestSabreParserCoverage:
    """Tests adicionales para SabreParser"""

    def test_parse_with_minimal_data(self):
        """test_parse_with_minimal_data."""
        parser = SabreParser()
        text = (
            "ETICKET RECEIPT\nRESERVATION CODE: ABC123\nPASSENGER: PEREZ/JUAN\n"
            "TICKET NUMBER: 1234567890123\n"
        )
        result = parser.parse(text)
        assert result.source_system == "SABRE"
        assert result.pnr == "ABC123"

    def test_parse_flights_empty(self):
        """test_parse_flights_empty."""
        parser = SabreParser()
        flights = parser._parse_flights("")
        assert flights == []

    def test_extract_currency_with_commas(self):
        """test_extract_currency_with_commas."""
        parser = SabreParser()
        currency, amount = parser.extract_currency_amount("USD 1,234.56")
        assert str(amount) == "1234.56"


class TestAmadeusParserCoverage:
    """Tests adicionales para AmadeusParser"""

    def test_parse_with_minimal_data(self):
        """test_parse_with_minimal_data."""
        parser = AmadeusParser()
        text = "ELECTRONIC TICKET RECEIPT\nBOOKING REF: XYZ789"
        result = parser.parse(text)
        assert result.source_system == "AMADEUS"

    def test_extract_pnr_fallback(self):
        """test_extract_pnr_fallback."""
        parser = AmadeusParser()
        pnr = parser.extract_field(
            "Booking ref: ABC123",
            [
                r"Booking ref\s*?:\s*([A-Z0-9]{6})",
                r"Booking reference\s*?:\s*([A-Z0-9]{6})",
            ],
        )
        assert pnr == "ABC123"


class TestKIUParserCoverage:
    """Tests adicionales para KIUParser"""

    def test_can_parse_kiusys(self):
        """test_can_parse_kiusys."""
        parser = KIUParser()
        assert parser.can_parse("KIUSYS.COM ticket data") is True

    def test_can_parse_passenger_receipt(self):
        """test_can_parse_passenger_receipt."""
        parser = KIUParser()
        assert parser.can_parse("PASSENGER ITINERARY RECEIPT") is True

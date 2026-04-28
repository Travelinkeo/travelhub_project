"""Tests adicionales para aumentar cobertura de parsers"""
import pytest
from core.parsers.sabre_parser import SabreParser
from core.parsers.amadeus_parser import AmadeusParser
from core.parsers.kiu_parser import KIUParser


@pytest.mark.django_db
class TestSabreParserCoverage:
    """Tests adicionales para SabreParser"""
    
    def test_parse_with_minimal_data(self):
        parser = SabreParser()
        text = "ETICKET RECEIPT\nRESERVATION CODE: ABC123"
        result = parser.parse(text)
        assert result.source_system == 'SABRE'
        assert result.pnr == 'ABC123'
    
    def test_parse_flights_empty(self):
        parser = SabreParser()
        flights = parser._parse_flights("")
        assert flights == []
    
    def test_extract_currency_with_commas(self):
        parser = SabreParser()
        currency, amount = parser.extract_currency_amount("USD 1,234.56")
        assert str(amount) == "1234.56"


@pytest.mark.django_db
class TestAmadeusParserCoverage:
    """Tests adicionales para AmadeusParser"""
    
    def test_parse_with_minimal_data(self):
        parser = AmadeusParser()
        text = "ELECTRONIC TICKET RECEIPT\nBOOKING REF: XYZ789"
        result = parser.parse(text)
        assert result.source_system == 'AMADEUS'
    
    def test_extract_pnr_fallback(self):
        parser = AmadeusParser()
        pnr = parser._extract_pnr("Booking ref: ABC123")
        assert pnr == 'ABC123'


@pytest.mark.django_db
class TestKIUParserCoverage:
    """Tests adicionales para KIUParser"""
    
    def test_can_parse_kiusys(self):
        parser = KIUParser()
        assert parser.can_parse("KIUSYS.COM ticket data") is True
    
    def test_can_parse_passenger_receipt(self):
        parser = KIUParser()
        assert parser.can_parse("PASSENGER ITINERARY RECEIPT") is True

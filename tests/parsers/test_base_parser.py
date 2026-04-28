"""Tests para BaseTicketParser"""
import pytest
from decimal import Decimal

from core.parsers.base_parser import BaseTicketParser, ParsedTicketData
from core.parsers.sabre_parser import SabreParser


class TestBaseParserMethods:
    """Tests para métodos comunes de BaseTicketParser"""
    
    def test_extract_currency_amount_usd(self):
        parser = SabreParser()
        currency, amount = parser.extract_currency_amount("USD 1,234.56")
        assert currency == "USD"
        assert amount == Decimal("1234.56")
    
    def test_extract_currency_amount_eur(self):
        parser = SabreParser()
        currency, amount = parser.extract_currency_amount("EUR 500.00")
        assert currency == "EUR"
        assert amount == Decimal("500.00")
    
    def test_extract_currency_amount_no_match(self):
        parser = SabreParser()
        currency, amount = parser.extract_currency_amount("No encontrado")
        assert currency is None
        assert amount is None
    
    def test_clean_text(self):
        parser = SabreParser()
        result = parser.clean_text("  Multiple   spaces   ")
        assert result == "Multiple spaces"
    
    def test_extract_field_first_pattern(self):
        parser = SabreParser()
        text = "Reservation Code: ABC123"
        result = parser.extract_field(text, [
            r'Reservation Code:\s*([A-Z0-9]+)',
            r'PNR:\s*([A-Z0-9]+)'
        ])
        assert result == "ABC123"
    
    def test_extract_field_second_pattern(self):
        parser = SabreParser()
        text = "PNR: XYZ789"
        result = parser.extract_field(text, [
            r'Reservation Code:\s*([A-Z0-9]+)',
            r'PNR:\s*([A-Z0-9]+)'
        ])
        assert result == "XYZ789"
    
    def test_extract_field_no_match(self):
        parser = SabreParser()
        text = "Some random text"
        result = parser.extract_field(text, [r'PNR:\s*([A-Z0-9]+)'])
        assert result == "No encontrado"


class TestParsedTicketData:
    """Tests para ParsedTicketData"""
    
    def test_to_dict(self):
        data = ParsedTicketData(
            source_system='TEST',
            pnr='ABC123',
            ticket_number='123456',
            passenger_name='John Doe',
            issue_date='2025-01-01',
            flights=[],
            fares={},
            raw_data={}
        )
        
        result = data.to_dict()
        assert result['SOURCE_SYSTEM'] == 'TEST'
        assert result['pnr'] == 'ABC123'
        assert result['numero_boleto'] == '123456'
        assert result['pasajero']['nombre_completo'] == 'John Doe'

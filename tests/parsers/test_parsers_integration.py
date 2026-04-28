"""Tests de integración para parsers"""
import pytest

from core.parsers.adapter import parse_ticket_with_new_parsers


class TestParsersIntegration:
    """Tests de integración para todos los parsers"""
    
    def test_sabre_detection(self):
        text = "ETICKET RECEIPT\nRESERVATION CODE: ABC123\nTicket Number: 1234567890"
        result = parse_ticket_with_new_parsers(text)
        assert result['SOURCE_SYSTEM'] == 'SABRE'
        assert 'error' not in result
    
    def test_amadeus_detection(self):
        text = "ELECTRONIC TICKET RECEIPT\nBOOKING REF: XYZ789"
        result = parse_ticket_with_new_parsers(text)
        assert result['SOURCE_SYSTEM'] == 'AMADEUS'
        assert 'error' not in result
    
    def test_kiu_detection(self):
        text = "KIUSYS.COM\nPASSENGER ITINERARY RECEIPT"
        result = parse_ticket_with_new_parsers(text)
        assert result['SOURCE_SYSTEM'] == 'KIU'
        assert 'error' not in result
    
    def test_copa_detection(self):
        text = "COPA AIRLINES\nLocalizador de reserva ABC123"
        result = parse_ticket_with_new_parsers(text)
        assert result['SOURCE_SYSTEM'] == 'COPA_SPRK'
        assert 'error' not in result
    
    def test_wingo_detection(self):
        text = "WINGO.COM\nCódigo de reserva XYZ789"
        result = parse_ticket_with_new_parsers(text)
        assert result['SOURCE_SYSTEM'] == 'WINGO'
        assert 'error' not in result
    
    def test_unknown_system(self):
        text = "Random text without any GDS markers"
        result = parse_ticket_with_new_parsers(text)
        assert 'error' in result

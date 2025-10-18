"""Parser refactorizado para boletos KIU"""
import re
from typing import Dict, Any
from bs4 import BeautifulSoup

from .base_parser import BaseTicketParser, ParsedTicketData


class KIUParser(BaseTicketParser):
    """Parser para boletos del sistema KIU"""
    
    def can_parse(self, text: str) -> bool:
        text_upper = text.upper()
        return 'KIUSYS.COM' in text_upper or 'PASSENGER ITINERARY RECEIPT' in text_upper
    
    def parse(self, text: str, html_text: str = "") -> ParsedTicketData:
        pnr = self._extract_pnr(text)
        ticket_number = self.extract_field(text, [
            r"TICKET N[BR]O\s*[:\s]*([0-9-]{8,})",
            r"TICKET'?S? NUMBER'?S?\s*[:\s]*([0-9-]{8,})"
        ])
        
        issue_date = self.extract_field(text, [
            r'ISSUE DATE/FECHA DE EMISION\s*[:\s]*([0-9]{1,2}\s+[A-Z]{3}\s+[0-9]{4})',
            r'ISSUE DATE\s*[:\s]*([0-9]{1,2}\s+[A-Z]{3}\s+[0-9]{4})'
        ])
        
        passenger_name = self._extract_passenger_name(text)
        airline = self._extract_airline(text)
        
        fares = {
            'tarifa_base': self.extract_field(text, [r'AIR FARE\s*[:\s]*([A-Z]{3}\s*[0-9,.]+)']),
            'total': self.extract_field(text, [r'TOTAL\s*[:\s]*([A-Z]{3}\s*[0-9,.]+)'])
        }
        
        fare_currency, fare_amount = self.extract_currency_amount(fares['tarifa_base'])
        total_currency, total_amount = self.extract_currency_amount(fares['total'])
        
        return ParsedTicketData(
            source_system='KIU',
            pnr=pnr,
            ticket_number=ticket_number,
            passenger_name=passenger_name,
            issue_date=self.normalize_date(issue_date) or issue_date,
            flights=[],
            fares={
                'fare_currency': fare_currency,
                'fare_amount': str(fare_amount) if fare_amount else None,
                'total_currency': total_currency,
                'total_amount': str(total_amount) if total_amount else None,
            },
            raw_data={
                'NUMERO_DE_BOLETO': ticket_number,
                'FECHA_DE_EMISION': issue_date,
                'NOMBRE_DEL_PASAJERO': passenger_name,
                'SOLO_CODIGO_RESERVA': pnr,
                'NOMBRE_AEROLINEA': airline,
                'TARIFA': fares['tarifa_base'],
                'TOTAL': fares['total'],
            }
        )
    
    def _extract_pnr(self, text: str) -> str:
        match = re.search(r"C1\s*/\s*([A-Z0-9]{6})", text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        
        booking_ref = self.extract_field(text, [r'BOOKING REF\.\s*[:\s]*(.+)'])
        if booking_ref != 'No encontrado':
            match = re.search(r'\b([A-Z0-9]{6})\b', booking_ref)
            if match:
                return match.group(1)
        return 'No encontrado'
    
    def _extract_passenger_name(self, text: str) -> str:
        raw = self.extract_field(text, [r'NAME\s*[:\s]*([A-ZÁÉÍÓÚÑ/ (),.-]{3,})'])
        if raw == 'No encontrado':
            return raw
        
        # Limpiar nombre
        raw = re.sub(r'[^A-ZÁÉÍÓÚÑ/ ]+', ' ', raw.upper())
        raw = re.sub(r'\s{2,}', ' ', raw).strip()
        return raw
    
    def _extract_airline(self, text: str) -> str:
        raw = self.extract_field(text, [r'ISSUING AIRLINE\s*[:\s]*([A-Z0-9 ,.&-]{3,})'])
        return self.normalize_airline_name(raw, None)

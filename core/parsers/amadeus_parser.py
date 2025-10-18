"""
Parser refactorizado para boletos AMADEUS.
"""

import re
from typing import Dict, Any, List

from .base_parser import BaseTicketParser, ParsedTicketData


class AmadeusParser(BaseTicketParser):
    """Parser para boletos del sistema AMADEUS"""
    
    def can_parse(self, text: str) -> bool:
        """Detecta si es un boleto AMADEUS"""
        text_upper = text.upper()
        return 'ELECTRONIC TICKET RECEIPT' in text_upper and 'BOOKING REF:' in text_upper
    
    def parse(self, text: str, html_text: str = "") -> ParsedTicketData:
        """Parsea boleto AMADEUS"""
        
        # Extraer PNR
        pnr = self._extract_pnr(text)
        
        # Extraer número de boleto
        ticket_number = self._extract_ticket_number(text)
        
        # Extraer fecha de emisión
        issue_date = self._extract_issue_date(text)
        
        # Extraer pasajero
        passenger_data = self._extract_passenger(text)
        
        # Extraer agencia
        agency_data = self._extract_agency(text)
        
        # Extraer vuelos
        flights = self._extract_flights(text)
        
        # Extraer tarifas
        fares = self._extract_fares(text)
        
        return ParsedTicketData(
            source_system='AMADEUS',
            pnr=pnr,
            ticket_number=ticket_number,
            passenger_name=passenger_data.get('nombre_completo', 'No encontrado'),
            issue_date=issue_date,
            flights=flights,
            fares=fares,
            agency=agency_data,
            raw_data={
                'pasajero': passenger_data,
                'agencia': agency_data,
                'vuelos': flights,
                'tarifas': fares,
            }
        )
    
    def _extract_pnr(self, text: str) -> str:
        """Extrae el PNR (Booking Reference)"""
        # Patrón: 223PPDBooking ref:
        match = re.search(r'([A-Z0-9]{6})Booking ref:', text)
        if match:
            return match.group(1)
        
        # Fallback
        match = re.search(r'Booking ref:\s*\n?\s*([A-Z0-9]{6})', text, re.IGNORECASE)
        if match:
            return match.group(1)
        
        return 'No encontrado'
    
    def _extract_ticket_number(self, text: str) -> str:
        """Extrae el número de ticket"""
        patterns = [
            r'(\d{3}-?\d{10})Ticket:',
            r'Ticket:\s*\n?\s*([\d-]+)',
            r'Ticket number\s*:\s*([\d-]+)',
            r'(\d{3}-\d{10})',
        ]
        return self.extract_field(text, patterns)
    
    def _extract_issue_date(self, text: str) -> str:
        """Extrae la fecha de emisión"""
        match = re.search(r'Issue date:\s*(\d{2}\s+[A-Z]+\s+\d{2,4})', text, re.IGNORECASE)
        if match:
            return match.group(1)
        
        match = re.search(r'Issuing Airline and date\s*:\s*[A-Z\s]+(\d{2}[A-Z]{3}\d{2})', text, re.IGNORECASE)
        return match.group(1) if match else 'No encontrado'
    
    def _extract_passenger(self, text: str) -> Dict[str, str]:
        """Extrae información del pasajero"""
        passenger = {
            'nombre_completo': 'No encontrado',
            'tipo': 'ADT'
        }
        
        match = re.search(r'Traveler\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+?)(?:\s+Agency|\s+\(([A-Z]{3})\))', text)
        if match:
            passenger['nombre_completo'] = match.group(1).strip()
            if match.group(2):
                passenger['tipo'] = match.group(2)
        
        return passenger
    
    def _extract_agency(self, text: str) -> Dict[str, str]:
        """Extrae información de la agencia"""
        agency = {
            'nombre': self.extract_field(text, [r'Agency\s+([A-Z\s&]+)']),
            'direccion': self.extract_field(text, [r'([A-Z0-9\s,.-]+)\s+(?:MIAMI|NEW YORK|CARACAS)']),
            'telefono': self.extract_field(text, [r'Telephone\s+([\d\s-]+)']),
            'iata': self.extract_field(text, [r'IATA\s+(\d+)']),
            'agente': self.extract_field(text, [r'Agent\s+(\d+)']),
        }
        return agency
    
    def _extract_flights(self, text: str) -> List[Dict[str, Any]]:
        """Extrae información de vuelos"""
        flights = []
        
        # Patrón para línea de vuelo AMADEUS
        pattern = r'([A-Z]+)\s+([A-Z]+)\s+([A-Z]{2})(\d{3,4})\s+([A-Z])\s+(\d{2}[A-Za-z]{3})\s+(\d{2}:\d{2})\s+(\d{2}:\d{2})\s+(Ok|Waitlist)\s+\d{2}[A-Za-z]{3}\s+\d{2}[A-Za-z]{3}\s+(\d+PC)\s+(\d{1,2}[A-Z])'
        
        for match in re.finditer(pattern, text):
            flight = {
                'segmento': len(flights) + 1,
                'origen': match.group(1),
                'destino': match.group(2),
                'aerolinea': match.group(3),
                'numero_vuelo': f"{match.group(3)}{match.group(4)}",
                'clase': match.group(5),
                'fecha_salida': match.group(6),
                'hora_salida': match.group(7),
                'hora_llegada': match.group(8),
                'estado': match.group(9),
                'equipaje': match.group(10),
                'asiento': match.group(11),
            }
            flights.append(flight)
        
        return flights
    
    def _extract_fares(self, text: str) -> Dict[str, Any]:
        """Extrae información de tarifas"""
        fares = {
            'forma_pago': self.extract_field(text, [r'Form of payment\s*:\s*([A-Z]+)']),
            'tarifa_base': self.extract_field(text, [r'Air Fare\s*:\s*([A-Z]{3}\s*[\d,.]+)']),
            'total': self.extract_field(text, [r'Total Amount\s*:\s*([A-Z]{3}\s*[\d,.]+)']),
        }
        
        # Extraer moneda y monto
        fare_currency, fare_amount = self.extract_currency_amount(fares['tarifa_base'])
        total_currency, total_amount = self.extract_currency_amount(fares['total'])
        
        fares['fare_currency'] = fare_currency
        fares['fare_amount'] = str(fare_amount) if fare_amount else None
        fares['total_currency'] = total_currency
        fares['total_amount'] = str(total_amount) if total_amount else None
        
        return fares

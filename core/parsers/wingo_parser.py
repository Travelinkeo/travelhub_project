"""Parser refactorizado para boletos Wingo"""
import re
from datetime import datetime
from typing import Dict, Any, List

from .base_parser import BaseTicketParser, ParsedTicketData


class WingoParser(BaseTicketParser):
    """Parser para reservas de Wingo (aerolínea low-cost)"""
    
    def can_parse(self, text: str) -> bool:
        text_upper = text.upper()
        return 'WINGO' in text_upper or 'WINGO.COM' in text_upper
    
    def parse(self, text: str, html_text: str = "") -> ParsedTicketData:
        pnr = self.extract_field(text, [r'(?:C[óo]digo de reserva|reserva)\s+([A-Z0-9]{6})'])
        passenger_name = self.extract_field(text, [r'Contacto\s+([A-Z\s]+)\s+Documento'])
        flights = self._extract_flights(text)
        
        return ParsedTicketData(
            source_system='WINGO',
            pnr=pnr,
            ticket_number=None,  # Wingo no genera número de boleto
            passenger_name=passenger_name,
            issue_date=datetime.now().strftime('%d/%m/%Y'),
            flights=flights,
            fares={},
            raw_data={
                'pasajero': {'nombre_completo': passenger_name, 'tipo': 'ADT'},
                'vuelos': flights,
                'fecha_creacion': datetime.now().strftime('%d/%m/%Y'),
            }
        )
    
    def _extract_flights(self, text: str) -> List[Dict[str, Any]]:
        flights = []
        
        # Vuelo de ida
        ida_match = re.search(
            r'Vuelo de ida.*?([A-Za-z]{3}, \d{1,2} [A-Za-z]{3})\s+(\d{2}:\d{2} [AP]M).*?Directo\s+(\d+h \d+min)\s+(\d{2}:\d{2} [AP]M)\s+([A-Za-z]+)\s+\(([A-Z]{3})\)\s+([A-Za-z]+)\s+\(([A-Z]{3})\)',
            text, re.DOTALL
        )
        if ida_match:
            flights.append({
                'numero_vuelo': 'WINGO',
                'origen': ida_match.group(5),
                'codigo_origen': ida_match.group(6),
                'fecha_salida': ida_match.group(1),
                'hora_salida': ida_match.group(2),
                'destino': ida_match.group(7),
                'codigo_destino': ida_match.group(8),
                'hora_llegada': ida_match.group(4),
                'duracion': ida_match.group(3),
                'aerolinea': 'Wingo',
                'cabina': 'GO BASIC'
            })
        
        # Vuelo de vuelta
        vuelta_match = re.search(
            r'Vuelo de vuelta.*?([A-Za-z]{3}, \d{1,2} [A-Za-z]{3})\s+(\d{2}:\d{2} [AP]M).*?Directo\s+(\d+h \d+min)\s+(\d{2}:\d{2} [AP]M)\s+([A-Za-z]+)\s+\(([A-Z]{3})\)\s+([A-Za-z]+)\s+\(([A-Z]{3})\)',
            text, re.DOTALL
        )
        if vuelta_match:
            flights.append({
                'numero_vuelo': 'WINGO',
                'origen': vuelta_match.group(5),
                'codigo_origen': vuelta_match.group(6),
                'fecha_salida': vuelta_match.group(1),
                'hora_salida': vuelta_match.group(2),
                'destino': vuelta_match.group(7),
                'codigo_destino': vuelta_match.group(8),
                'hora_llegada': vuelta_match.group(4),
                'duracion': vuelta_match.group(3),
                'aerolinea': 'Wingo',
                'cabina': 'GO BASIC'
            })
        
        return flights

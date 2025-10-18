"""Parser refactorizado para boletos Copa SPRK"""
import re
from typing import Dict, Any, List

from .base_parser import BaseTicketParser, ParsedTicketData


class CopaParser(BaseTicketParser):
    """Parser para boletos de Copa Airlines (sistema SPRK)"""
    
    def can_parse(self, text: str) -> bool:
        text_upper = text.upper()
        return ('COPA AIRLINES' in text_upper and 'LOCALIZADOR DE RESERVA' in text_upper) or 'SPRK' in text_upper
    
    def parse(self, text: str, html_text: str = "") -> ParsedTicketData:
        pnr = self.extract_field(text, [r'Localizador de reserva\s+([A-Z0-9]{6})'])
        ticket_number = self.extract_field(text, [r'Billete electr[óo]nico\s+(\d+)'])
        issue_date = self.extract_field(text, [r'Fecha de emisi[óo]n\s+(\d{2}[A-Z]{3}\.\d{2})'])
        
        passenger_data = self._extract_passenger(text)
        flights = self._extract_flights(text)
        
        return ParsedTicketData(
            source_system='COPA_SPRK',
            pnr=pnr,
            ticket_number=ticket_number,
            passenger_name=passenger_data.get('nombre_completo', 'No encontrado'),
            issue_date=issue_date,
            flights=flights,
            fares={},
            raw_data={
                'pasajero': passenger_data,
                'vuelos': flights,
                'fecha_creacion': issue_date,
            }
        )
    
    def _extract_passenger(self, text: str) -> Dict[str, str]:
        match = re.search(r'(MR|MRS|MS)\s+([A-Z\s]+)\s+\(ADT\)', text)
        if match:
            return {
                'nombre_completo': f"{match.group(1)} {match.group(2).strip()}",
                'tipo': 'ADT'
            }
        return {'nombre_completo': 'No encontrado', 'tipo': 'ADT'}
    
    def _extract_flights(self, text: str) -> List[Dict[str, Any]]:
        flights = []
        pattern = r'Copa Airlines\s+(\d+)\s+([^,]+),\s+([A-Z]{2})\s+([A-Z]{2}\. \d{2}[A-Z]{3}\.)\s+(\d{2}:\d{2})\s+([^,]+),\s+([A-Z]{2})\s+([A-Z]{2}\. \d{2}[A-Z]{3}\.)\s+(\d{2}:\d{2})\s+([A-Z])\s+([A-Z])'
        
        for match in re.finditer(pattern, text):
            flights.append({
                'numero_vuelo': f"CM{match.group(1)}",
                'origen': match.group(2).strip(),
                'codigo_origen': match.group(3),
                'fecha_salida': match.group(4),
                'hora_salida': match.group(5),
                'destino': match.group(6).strip(),
                'codigo_destino': match.group(7),
                'fecha_llegada': match.group(8),
                'hora_llegada': match.group(9),
                'clase': match.group(10),
                'cabina': match.group(11),
                'aerolinea': 'Copa Airlines'
            })
        return flights

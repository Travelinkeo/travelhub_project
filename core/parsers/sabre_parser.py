"""
Parser refactorizado para boletos SABRE.
"""

import re
from typing import Dict, Any, List

from .base_parser import BaseTicketParser, ParsedTicketData
from core.parsing_utils import _inferir_fecha_llegada


class SabreParser(BaseTicketParser):
    """Parser para boletos del sistema SABRE"""
    
    def can_parse(self, text: str) -> bool:
        """Detecta si es un boleto SABRE"""
        text_upper = text.upper()
        has_receipt = 'ETICKET RECEIPT' in text_upper or 'RECIBO DE BOLETO ELECTRÓNICO' in text_upper or 'RECIBO DE BOLETO ELECTRONICO' in text_upper
        has_reservation = 'RESERVATION CODE' in text_upper or 'CÓDIGO DE RESERVACIÓN' in text_upper or 'CODIGO DE RESERVACION' in text_upper
        return has_receipt and has_reservation
    
    def parse(self, text: str, html_text: str = "") -> ParsedTicketData:
        """Parsea boleto SABRE"""
        
        # Extraer datos básicos
        passenger_name = self.extract_field(text, [
            r'(?:Prepared For|Preparado para)\s*\n\s*([A-ZÁÉÍÓÚ0-9\-\/\[\s,\.]+?)(?:\s*\[|\n|$)'
        ])
        
        document_id = self.extract_field(text, [
            r'(?:Prepared For|Preparado para)\s*[A-ZÁÉÍÓÚ/\s]+\s*\[([A-Z0-9]+)\]'
        ])
        
        pnr = self.extract_field(text, [
            r'(?:Reservation Code|CÓDIGO DE RESERVACIÓN)\s*[:\t\s]*([A-Z0-9]+)'
        ])
        
        # Extraer localizador de aerolínea (viene después de "Código de reservación de la aerolínea")
        airline_locator = self.extract_field(text, [
            r'(?:Airline Record Locator|Código de reservación de\s*la\s*aerolínea)\s*[:\t\s\n]*([A-Z0-9]{6})',
            r'(?:Record Locator)\s*[:\t\s]*([A-Z0-9]{6})'
        ])
        
        issue_date = self.extract_field(text, [
            r'(?:Issue Date|Fecha de Emisión|FECHA DE EMISIÓN)\s*[:\t\s]*([\d]{1,2}\s+\w{3}\s+[\d]{2})'
        ])
        
        ticket_number = self.extract_field(text, [
            r'(?:Ticket Number|NÚMERO DE BOLETO)\s*[:\t\s]*([\d]+)'
        ])
        
        airline = self.extract_field(text, [
            r'(?:Issuing Airline|AEROLÍNEA EMISORA)\s*[:\t\s]*([A-ZÁÉÍÓÚ0-9 \/]+)'
        ])
        
        agent = self.extract_field(text, [
            r'(?:Issuing Agent|AGENTE EMISOR)\s*[:\t\s]*([^\n\r]+)'
        ])
        
        iata = self.extract_field(text, [
            r'(?:IATA Number|IATA)\s*[:\t\s]*([\d]+)'
        ])
        
        # Extraer vuelos
        flights = self._parse_flights(text, airline_locator)
        
        # Extraer tarifas
        fare_raw = self.extract_field(text, [
            r'Fare\s+([A-Z]{3}\s*[0-9,.]+)',
            r'Tarifa\s+([A-Z]{3}\s*[0-9,.]+)'
        ])
        
        total_raw = self.extract_field(text, [
            r'Total\s+([A-Z]{3}\s*[0-9,.]+)'
        ])
        
        fare_currency, fare_amount = self.extract_currency_amount(fare_raw)
        total_currency, total_amount = self.extract_currency_amount(total_raw)
        
        # Normalizar fechas
        issue_date_iso = self.normalize_date(issue_date)
        
        # Normalizar nombre de aerolínea
        airline_normalized = self.normalize_airline_name(
            airline,
            flights[0].get('numero_vuelo') if flights else None
        )
        
        return ParsedTicketData(
            source_system='SABRE',
            pnr=pnr,
            ticket_number=ticket_number,
            passenger_name=passenger_name,
            issue_date=issue_date_iso or issue_date,
            flights=flights,
            fares={
                'fare_currency': fare_currency,
                'fare_amount': str(fare_amount) if fare_amount else None,
                'total_currency': total_currency,
                'total_amount': str(total_amount) if total_amount else None,
            },
            agency={
                'agent': agent,
                'iata': iata,
            },
            raw_data={
                'pasajero': {
                    'nombre_completo': passenger_name,
                    'documento_identidad': document_id or None,
                },
                'reserva': {
                    'codigo_reservacion': pnr,
                    'numero_boleto': ticket_number,
                    'fecha_emision_iso': issue_date_iso,
                    'aerolinea_emisora': airline_normalized,
                    'agente_emisor': {
                        'nombre': agent,
                        'numero_iata': iata,
                    },
                },
                'itinerario': {
                    'vuelos': flights,
                },
            }
        )
    
    def _parse_flights(self, text: str, airline_locator: str = None) -> List[Dict[str, Any]]:
        """Extrae información de vuelos del texto"""
        flights = []
        
        # Remover sección de agente emisor para evitar confusión con códigos de vuelo
        text_clean = re.sub(
            r'(?:Issuing Agent|AGENTE EMISOR)\s*[:\t\s]*[^\n\r]+',
            '',
            text,
            flags=re.IGNORECASE
        )
        
        # Extraer todas las horas del documento
        all_times = re.findall(r'(?:Time|Hora)\s*(\d{1,2}:\d{2})', text_clean)
        
        # Dividir por bloques de vuelo
        flight_blocks = re.split(
            r'This is not a boarding pass|Esta no es una tarjeta de embarque',
            text_clean
        )
        
        for block in flight_blocks:
            block = block.strip()
            if not block or not re.search(r'\b[A-Z]{2}\s?\d{1,4}\b', block):
                continue
            
            flight = {}
            lines = [line.strip() for line in block.splitlines() if line.strip()]
            
            # Buscar número de vuelo
            for i, line in enumerate(lines):
                match = re.search(r'\b([A-Z]{2}\s*\d{1,4})\b', line)
                if match:
                    flight['numero_vuelo'] = match.group(1).replace(' ', '')
                    
                    # Buscar aerolínea en líneas anteriores
                    airline_parts = []
                    for j in range(i - 1, max(-1, i - 3), -1):
                        prev_line = lines[j]
                        if re.search(r'\d{2}\s+\w{3}\s+\d{2}', prev_line) or ',' in prev_line:
                            break
                        airline_parts.insert(0, prev_line)
                    
                    if airline_parts:
                        raw_airline = ' '.join(airline_parts)
                        flight['aerolinea'] = self.normalize_airline_name(
                            raw_airline,
                            flight.get('numero_vuelo')
                        )
                    break
            
            if not flight.get('numero_vuelo'):
                continue
            
            # Extraer fechas (buscar específicamente Salida/Departure y Llegada/Arrival)
            departure_match = re.search(r'(?:Salida|Departure):\s*(\d{1,2}\s+\w{3}\s+\d{2})', block)
            if departure_match:
                flight['fecha_salida'] = departure_match.group(1)
            else:
                # Fallback: buscar fecha después del número de vuelo, NO la primera del bloque
                flight_num = flight.get('numero_vuelo', '')
                if flight_num:
                    # Buscar fecha que viene después del número de vuelo
                    pattern = rf'{re.escape(flight_num)}.*?(\d{{1,2}}\s+\w{{3}}\s+\d{{2}})'
                    date_match = re.search(pattern, block, re.DOTALL)
                    if date_match:
                        flight['fecha_salida'] = date_match.group(1)
            
            arrival_match = re.search(r'(?:Llegada|Arrival):\s*(\d{1,2}\s+\w{3}\s+\d{2})', block)
            if arrival_match:
                flight['fecha_llegada'] = arrival_match.group(1)
            else:
                flight['fecha_llegada'] = None
            
            # Extraer horas
            if all_times:
                flight['hora_salida'] = all_times.pop(0)
            if all_times:
                flight['hora_llegada'] = all_times.pop(0)
            
            # Extraer origen y destino
            cities = re.findall(r'([A-ZÁÉÍÓÚ -]+,\s*[A-ZÁÉÍÓÚ -]+)', block)
            if len(cities) >= 2:
                origin_parts = cities[0].split(',')
                dest_parts = cities[1].split(',')
                flight['origen'] = {
                    'ciudad': origin_parts[0].strip(),
                    'pais': origin_parts[1].strip() if len(origin_parts) > 1 else None
                }
                flight['destino'] = {
                    'ciudad': dest_parts[0].strip(),
                    'pais': dest_parts[1].strip() if len(dest_parts) > 1 else None
                }
            
            # Otros detalles
            cabin_match = re.search(r'Cabina\s+([A-Za-z]+)', block, re.IGNORECASE)
            if cabin_match:
                flight['cabina'] = cabin_match.group(1)
            
            bag_match = re.search(r'(?:Límite de equipaje|Baggage Allowance)\s*([A-Z0-9]+)', block, re.IGNORECASE)
            if bag_match:
                flight['equipaje'] = bag_match.group(1)
            
            # Agregar localizador de aerolínea si existe
            flight['codigo_reservacion_local'] = airline_locator or 'No encontrado'
            
            flights.append(flight)
        
        return flights

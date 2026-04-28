
import re
import logging
from typing import Dict, Any, List, Optional
from core.parsers.base_parser import BaseTicketParser, ParsedTicketData

logger = logging.getLogger(__name__)

class AmadeusParser(BaseTicketParser):
    """
    Parser for Amadeus Electronic Ticket Receipts.
    Identified by 'Electronic Ticket Receipt' and 'CheckMyTrip' markers.
    """
    
    def can_parse(self, text: str) -> bool:
        """Check if text looks like an Amadeus ticket."""
        markers = [
            'Electronic Ticket Receipt',
            'CheckMyTrip',
            'Booking ref:',
            'Amadeus'
        ]
        count = sum(1 for m in markers if m.lower() in text.lower())
        return count >= 1

    def parse(self, text: str, html_text: str = "", pdf_path: str = None) -> ParsedTicketData:
        """Main parsing method with robust AI fallback."""
        # --- PHASE 1: REGEX PARSING (Nativo) ---
        pnr = self.extract_field(text, [
            r'Booking ref\s*:?\s*([A-Z0-9]{6})',
            r'Booking reference\s*:?\s*([A-Z0-9]{6})',
            r'Record Locator\s*([A-Z0-9]{6})',
            r'AMADEUS\s+RESERVATION\s+NUMBER[:\s]+([A-Z0-9]{6})',
            r'RESERVA[^\n]*?([A-Z0-9]{6})'
        ])
        
        ticket_number = self.extract_field(text, [
            r'Ticket\s*(?:number)?\s*:?\s*(\d{3}[-\s]?\d{10})',
            r'Ticket\s*:\s*(\d{3}[-\s]?\d{10})',
            r'ETICKET\s*NBR[:\s]*(\d{3}[-\s]?\d{10})',
            r'(\d{13})'
        ])
        if ticket_number != 'No encontrado':
            ticket_number = re.sub(r'[-\s]', '', ticket_number)

        passenger_name = self._extract_passenger(text) or "No encontrado"
        issue_date = self.extract_field(text, [
            r'Date\s*:\s*(\d{2}\s?[A-Z]{3,}\s?\d{2,4})',
            r'Fecha\s*:\s*(\d{2}\s?[A-Z]{3,}\s?\d{2,4})',
            r'Issued\s*date\s*[:\s]+([^\n]+)'
        ])

        # --- PHASE 2: AI REINFORCEMENT (Deep Integrity) ---
        # Si faltan campos críticos o el PNR es 'No encontrado', usamos IA.
        if pnr == 'No encontrado' or passenger_name == 'No encontrado' or ticket_number == 'No encontrado':
            logger.info("Amadeus Native Regex incomplete. Triggering AI Reinforcement.")
            try:
                from core.parsers.ai_universal_parser import UniversalAIParser
                ai_parser = UniversalAIParser()
                # Pasamos el texto y pdf_path a la IA
                ai_data = ai_parser.parse(text, pdf_path=pdf_path)
                
                if ai_data and "error" not in ai_data:
                    # Si es multi-pax, nos quedamos con el primero por ahora (o el que coincida si se implementa más lógica)
                    if ai_data.get('is_multi_pax'):
                        ai_data = ai_data['tickets'][0]
                    
                    # Enriquecer o sobreescribir si la IA encontró datos
                    if pnr == 'No encontrado': pnr = ai_data.get('CODIGO_RESERVA') or pnr
                    if passenger_name == 'No encontrado': passenger_name = ai_data.get('NOMBRE_DEL_PASAJERO') or passenger_name
                    if ticket_number == 'No encontrado': ticket_number = ai_data.get('NUMERO_DE_BOLETO') or ticket_number
                    
                    return ParsedTicketData(
                        source_system='AMADEUS',
                        pnr=pnr,
                        ticket_number=ticket_number,
                        passenger_name=passenger_name,
                        issue_date=ai_data.get('FECHA_DE_EMISION') or issue_date,
                        flights=ai_data.get('vuelos', []),
                        fares={
                            'fare_amount': ai_data.get('TARIFA'),
                            'tax_amount': ai_data.get('IMPUESTOS'),
                            'total_amount': ai_data.get('TOTAL'),
                            'currency': ai_data.get('TOTAL_MONEDA')
                        },
                        es_remision=ai_data.get('es_remision', False),
                        raw_data=ai_data
                    )
            except Exception as e:
                logger.error(f"Fallo en AI Reinforcement de Amadeus: {e}")

        # Fallback a itinerario regex si la IA falló o no fue necesaria
        flights = self._extract_itinerary(text)
        
        return ParsedTicketData(
            source_system='AMADEUS',
            pnr=pnr,
            ticket_number=ticket_number,
            passenger_name=passenger_name,
            issue_date=issue_date,
            flights=flights,
            fares={},
            agency={},
            raw_data={'text_snippet': text[:500]}
        )

    def _extract_passenger(self, text: str) -> Optional[str]:
        # Cleaner logic for passenger name
        patterns = [
            r'Traveler\s+(?:MR|MRS|MS|MISS)?\s*([^\n]+?)\s+(?:Agency|Ticket|Booking)',
            r'Name\s*:\s*([^\n]+)',
            r'-([A-Z\s]+?)\s+\d{3}-' # Case from table rows
        ]
        for p in patterns:
            match = re.search(p, text, re.IGNORECASE)
            if match:
                name = match.group(1).strip()
                # Remove titles and suffixes
                name = re.sub(r'\((?:ADT|CHD|INF)\)', '', name)
                name = re.sub(r'\b(?:MR|MRS|MS|MISS|MSTR)\b', '', name, flags=re.IGNORECASE)
                return name.strip()
        return None

    def _extract_itinerary(self, text: str) -> List[Dict[str, Any]]:
        segments = []
        lines = text.split('\n')
        
        # Strategy A: Table Format (CARACAS ISTANBUL TK0224 U 05Dec 11:35 06:20)
        regex_table = r'([A-Z\s,]+)\s+([A-Z\s,]+)\s+([A-Z0-9]{2,3}\s?\d{1,4})\s+([A-Z])\s+(\d{2}[A-Za-z]{3})\s+(\d{2}:\d{2})\s+(\d{2}:\d{2})'
        
        for line in lines:
            match = re.search(regex_table, line.strip())
            if match:
                origin = match.group(1).strip()
                if 'DEPARTURE' in origin.upper() or 'FROM' in origin.upper(): continue
                
                segments.append({
                    'origen': origin,
                    'destino': match.group(2).strip(),
                    'numero_vuelo': match.group(3).replace(' ', ''),
                    'clase': match.group(4),
                    'fecha_salida': match.group(5),
                    'hora_salida': match.group(6),
                    'hora_llegada': match.group(7),
                    'aerolinea': match.group(3).strip()[:2]
                })

        if segments: return segments

        # Strategy B: Verbose Format (Departure/Arrival headers)
        current_flight = {}
        for i, line in enumerate(lines):
            line = line.strip()
            
            # Flight line before Departure: "Turkish Airlines TK 224"
            flight_match = re.search(r'([A-Z0-9]{2})\s?(\d{3,4})', line)
            if flight_match and "Departure" in (lines[i+1] if i+1 < len(lines) else ""):
                 current_flight['numero_vuelo'] = flight_match.group(1) + flight_match.group(2)
                 current_flight['aerolinea'] = flight_match.group(1)

            if line.startswith("Departure"):
                match = re.search(r'Departure\s+(\d{1,2}\s+[A-Za-z]+)\s+(\d{2}:\d{2})\s+(.+)', line)
                if match:
                    current_flight['fecha_salida'] = match.group(1)
                    current_flight['hora_salida'] = match.group(2)
                    current_flight['origen'] = match.group(3).strip()

            elif line.startswith("Arrival") and current_flight:
                match = re.search(r'Arrival\s+(\d{1,2}\s+[A-Za-z]+)\s+(\d{2}:\d{2})\s+(.+)', line)
                if match:
                    current_flight['hora_llegada'] = match.group(2)
                    current_flight['destino'] = match.group(3).strip()

            elif line.startswith("Class") and current_flight:
                match = re.search(r'Class\s+.*?\(([A-Z])\)', line)
                if match:
                    current_flight['clase'] = match.group(1)
                    segments.append(current_flight)
                    current_flight = {}

        return segments


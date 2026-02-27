
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

    def parse(self, text: str, html_text: str = "") -> ParsedTicketData:
        """Main parsing method with Gemini fallback."""
        # --- PHASE 1: REGEX PARSING ---
        pnr = self.extract_field(text, [
            r'Booking ref\s*:?\s*([A-Z0-9]{6})',
            r'Booking reference\s*:?\s*([A-Z0-9]{6})',
            r'Record Locator\s*([A-Z0-9]{6})'
        ])
        
        ticket_number = self.extract_field(text, [
            r'Ticket\s*(?:number)?\s*:?\s*(\d{3}[-\s]?\d{10})',
            r'Ticket\s*:\s*(\d{3}[-\s]?\d{10})'
        ])
        if ticket_number != 'No encontrado':
            ticket_number = re.sub(r'[-\s]', '', ticket_number)

        passenger_name = self._extract_passenger(text) or "No encontrado"
        
        passenger_document = self.extract_field(text, [
            r'Form of Identification\s+(?:PASSPORT|ID|DOC|NID)?\s*([A-Z0-9]+)',
            r'FOID\s*-\s*(?:ID|PP)?\s*([A-Z0-9]+)'
        ])

        # Amounts
        fares = {}
        amount_match = re.search(r'(?:Total Amount|Total|Grand Total)\s*:?\s*([A-Z]{3})\s*([\d,.]+)', text, re.IGNORECASE | re.DOTALL)
        if not amount_match:
             amount_match = re.search(r'\n([A-Z]{3})\s*([\d,.]+)\s*\n', text)
        
        if amount_match:
            currency = amount_match.group(1)
            amount_str = amount_match.group(2).replace(',', '')
            try:
                fares['total_amount'] = float(amount_str)
                fares['total_currency'] = currency
                fares['total'] = f"{currency} {amount_str}"
            except ValueError:
                pass
        
        # Itinerary
        flights = self._extract_itinerary(text)
        
        issue_date = self.extract_field(text, [
            r'Issue date\s*:?\s*(\d{1,2}\s+[A-Za-z]+\s+\d{2,4})',
            r'Date\s+of\s+issue\s*:?\s*(\d{1,2}\s+[A-Za-z]{3}\s+\d{2})'
        ])

        # Agency
        agency_name = self.extract_field(text, [r'Agency\s+([^\n]+?)(?:\s+Agent|\s+Telephone|\n)'])
        agency_iata = self.extract_field(text, [r'IATA\s+(\d+)'])
        
        agency = {}
        if agency_name != 'No encontrado': agency['name'] = agency_name
        if agency_iata != 'No encontrado': agency['iata'] = agency_iata

        # --- PHASE 2: GEMINI FALLBACK ---
        # If crucial data is missing, we use Gemini to "fix" it.
        if pnr == 'No encontrado' or not flights:
            logger.info(f"Amadeus Regex failed for PNR={pnr}, flights={len(flights)}. Triggering Gemini Fallback.")
            try:
                from .gemini_parser import GeminiParser
                ai_parser = GeminiParser()
                ai_data = ai_parser.parse(text, html_text)
                
                # Merge logic: AI overrides if it found something better
                if pnr == 'No encontrado' and ai_data.get('pnr'):
                    pnr = ai_data['pnr']
                
                if not flights and ai_data.get('vuelos'):
                    flights = ai_data['vuelos']
                    
                if passenger_name == 'No encontrado' and ai_data.get('pasajero', {}).get('nombre_completo'):
                    passenger_name = ai_data['pasajero']['nombre_completo']
                    
                if ticket_number == 'No encontrado' and ai_data.get('numero_boleto'):
                    ticket_number = ai_data['numero_boleto']
            except Exception as e:
                logger.error(f"Amadeus Gemini Fallback error: {e}")

        return ParsedTicketData(
            source_system='Amadeus',
            pnr=pnr,
            ticket_number=ticket_number,
            passenger_name=passenger_name,
            passenger_document=passenger_document if passenger_document != 'No encontrado' else None,
            issue_date=issue_date,
            flights=flights,
            fares=fares,
            agency=agency,
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


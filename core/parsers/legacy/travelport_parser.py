
import re
import logging
from typing import Dict, Any, List, Optional
from core.parsers.base_parser import BaseTicketParser, ParsedTicketData

logger = logging.getLogger(__name__)

class TravelportParser(BaseTicketParser):
    """
    Parser for Travelport (Galileo/Worldspan/Apollo) Smartpoint scripts and emails.
    Identified by 'Travelport', 'Galileo', 'Worldspan' or 'ViewTrip' markers.
    """
    
    def can_parse(self, text: str) -> bool:
        """Check if text looks like a Travelport ticket."""
        markers = [
            'Travelport',
            'Galileo',
            'Worldspan',
            'ViewTrip',
            'Electronic Ticket Receipt',
            'APOLLO'
        ]
        # Travelport documents often have specific layouts or headers
        count = sum(1 for m in markers if m.lower() in text.lower())
        return count >= 1

    def parse(self, text: str, html_text: str = "", pdf_path: str = None) -> ParsedTicketData:
        """Main parsing method with robust AI fallback."""
        
        # --- PHASE 1: REGEX PARSING (Nativo) ---
        pnr = self.extract_field(text, [
            r'BOOKING REFERENCE\s*[:\s]*([A-Z0-9]{6})',
            r'RESERVATION CODE\s*[:\s]*([A-Z0-9]{6})',
            r'GALILEO REFERENCE\s*[:\s]*([A-Z0-9]{6})',
            r'WORLDSPAN REFERENCE\s*[:\s]*([A-Z0-9]{6})',
            r'VENDOR LOCATOR\s*[:\s]*([A-Z0-9]{6})'
        ])
        
        ticket_number = self.extract_field(text, [
            r'TICKET\s*NUMBER\s*[:\s]*(\d{3}[-\s]?\d{10})',
            r'DOCUMENT\s*NUMBER\s*[:\s]*(\d{3}[-\s]?\d{10})',
            r'ETKT\s*(\d{13})'
        ])
        if ticket_number != 'No encontrado':
            ticket_number = re.sub(r'[-\s]', '', ticket_number)

        passenger_name = self.extract_passenger_name_robust(text)
        
        issue_date = self.extract_field(text, [
            r'ISSUED\s*DATE\s*[:\s]*(\d{2}\s?[A-Z]{3,}\s?\d{2,4})',
            r'DATE\s*OF\s*ISSUE\s*[:\s]*(\d{2}\s?[A-Z]{3,}\s?\d{2,4})'
        ])

        # --- PHASE 2: AI REINFORCEMENT (Deep Integrity) ---
        # Si faltan campos críticos o el PNR es 'No encontrado', usamos IA.
        if pnr == 'No encontrado' or passenger_name == 'No encontrado' or ticket_number == 'No encontrado':
            logger.info("Travelport Native Regex incomplete. Triggering AI Reinforcement.")
            try:
                from core.parsers.ai_universal_parser import UniversalAIParser
                ai_parser = UniversalAIParser()
                ai_data = ai_parser.parse(text, pdf_path=pdf_path)
                
                if ai_data and "error" not in ai_data:
                    if ai_data.get('is_multi_pax'):
                        ai_data = ai_data['tickets'][0]
                    
                    if pnr == 'No encontrado': pnr = ai_data.get('CODIGO_RESERVA') or pnr
                    if passenger_name == 'No encontrado': passenger_name = ai_data.get('NOMBRE_DEL_PASAJERO') or passenger_name
                    if ticket_number == 'No encontrado': ticket_number = ai_data.get('NUMERO_DE_BOLETO') or ticket_number
                    
                    return ParsedTicketData(
                        source_system='TRAVELPORT',
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
                logger.error(f"Fallo en AI Reinforcement de Travelport: {e}")

        return ParsedTicketData(
            source_system='TRAVELPORT',
            pnr=pnr,
            ticket_number=ticket_number,
            passenger_name=passenger_name,
            issue_date=issue_date,
            flights=[], # Itinerary parsing for Travelport usually needs AI due to high variability
            fares={},
            agency={},
            raw_data={'text_snippet': text[:500]}
        )

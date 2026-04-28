"""
Parser para boletos del sistema SABRE con soporte de IA y reemisiones.
"""

import re
import logging
from decimal import Decimal
from typing import Dict, Any, List, Optional

from .base_parser import BaseTicketParser, ParsedTicketData

logger = logging.getLogger(__name__)

class SabreParser(BaseTicketParser):
    """Parser para boletos del sistema SABRE"""
    
    def can_parse(self, text: str) -> bool:
        """Detecta si es un boleto SABRE"""
        text_upper = text.upper()
        return 'ETICKET RECEIPT' in text_upper and 'RESERVATION CODE' in text_upper
    
    def parse(self, text: str, html_text: str = "") -> ParsedTicketData:
        """Parsea boleto SABRE con refuerzo de IA"""
        from core.services.ai_engine import ai_engine
        from core.services.data_healer import DataHealer
        from core.models.ai_schemas import ResultadoParseoSchema
        
        # 1. Detección de Reemisión (Sabre Markers)
        es_remision = False
        if re.search(r'\b(?:EXCH|EXCHANGE|REEMISION|RE-ISSUE)\b', text, re.IGNORECASE):
            es_remision = True
            logger.info("🎯 Detectado marcador de reemisión en Sabre.")

        # 2. Extraer datos básicos (Regex)
        passenger_name = self.extract_passenger_name_robust(text)
        if passenger_name == 'No encontrado':
             passenger_name = self.extract_field(text, [
                r'(?:Prepared For|Preparado para)\s*\n\s*([A-ZÁÉÍÓÚ0-9\-\/\[\s,\.]+?)(?:\s*\[|\n|$)'
             ])
        
        pnr = self.extract_field(text, [
            r'(?:Reservation Code|C[OÓ]DIGO DE RESERVA(?:CI[OÓ]N)?)\s*[:\t\s]*([A-Z0-9]{6})'
        ])
        
        ticket_number = self.extract_field(text, [
            r'(?:Ticket Number|N[ÚU]MERO DE BOLETO|BOLETO)\s*[:\t\s]*([0-9]{13})'
        ])

        # --- AI REINFORCEMENT ---
        if pnr == 'No encontrado' or ticket_number == 'No encontrado' or passenger_name == 'No encontrado':
            logger.info("Sabre Native Regex incomplete. Triggering AI Reinforcement.")
            ai_res = ai_engine.call_gemini(
                prompt=f"Analiza este boleto de Sabre:\n{text}",
                response_schema=ResultadoParseoSchema,
                system_instruction=(
                    "Eres un experto en Sabre GDS. Extrae con precisión milimétrica:\n"
                    "- Reservation Code (6 caracteres), Ticket Number (13 dígitos), Nombre del Pasajero.\n"
                    "- ITINERARIO COMPLETO: para cada segmento de vuelo, extrae: numero_vuelo, origen (solo la CIUDAD), "
                    "destino (solo la CIUDAD), fecha_salida (YYYY-MM-DD), hora_salida (HH:MM formato 24h), "
                    "hora_llegada (HH:MM formato 24h), y localizador_aerolinea si difiere del PNR principal.\n"
                    "- JAMÁS mezcles las horas de un segmento con otro.\n"
                    "- Identifica si es remisión (busca EXCH, cambios de tarifa, o Tarifa > Total)."
                )
            )
            
            try:
                validated_res = DataHealer.heal_and_validate(ResultadoParseoSchema, ai_res)
                ai_data = validated_res.dict()
                boletos = ai_data.get('boletos', [])
                if boletos:
                    b = boletos[0]
                    if pnr == 'No encontrado': pnr = b.get('codigo_reserva')
                    if passenger_name == 'No encontrado': passenger_name = b.get('nombre_pasajero')
                    if ticket_number == 'No encontrado': ticket_number = b.get('numero_boleto')
                    if not es_remision: es_remision = b.get('es_remision', False)
            except Exception as e:
                logger.error(f"Fallo en AI Reinforcement de Sabre: {e}")

        # 3. Metadatos adicionales
        solo_nombre_pasajero = "Cliente"
        if passenger_name and passenger_name != "No encontrado":
            if '/' in passenger_name:
                parts = passenger_name.split('/')
                if len(parts) > 1:
                    solo_nombre_pasajero = parts[1].strip().split()[0]
            else:
                solo_nombre_pasajero = passenger_name.strip().split()[0]
        
        document_id = self.extract_field(text, [
            r'(?:Prepared For|Preparado para)\s*[:\t\s]*\n?\s*[^\[\n]+\s*\[([A-Z0-9]+)\]',
            r'\[([A-Z0-9]{5,20})\]',
            r'(?:NÚMERO DE CLIENTE|Customer Number)\s*[:\t\s]*([A-Z0-9-]+)',
        ])

        airline_locator = self.extract_field(text, [
            # Standard keyword followed directly by code on same line
            r'(?:Airline Record Locator|C[oó]digo de reservaci[oó]n de la aerol[\u00ed\u0069]nea)\s*[:\t\s]*([A-Z0-9]{4,7})(?=\s|$)',
        ])
        if airline_locator == 'No encontrado' or (airline_locator and not re.search(r'\d', airline_locator)):
            # Multiline: 'aerolínea B3NEK9' — code must have at least 1 digit
            m = re.search(r'aerol[\u00edi]nea\s*\n?\s*([A-Z0-9]{4,7})\b', text, re.IGNORECASE)
            if m and re.search(r'\d', m.group(1)):
                airline_locator = m.group(1)
            else:
                # Fallback: 'Código de reservación de la\naerolínea B3NEK9'
                m2 = re.search(r'C[oó]digo de reservaci[oó]n de[\s\S]{0,40}?aerol[\u00edi]nea\s+([A-Z0-9]{4,7})\b', text, re.IGNORECASE)
                if m2 and re.search(r'\d', m2.group(1)):
                    airline_locator = m2.group(1)
                else:
                    airline_locator = None
        if airline_locator == 'No encontrado':
            airline_locator = None
        
        issue_date = self.extract_field(text, [
            r'(?:Issue Date|Fecha de Emisi[óo]n|FECHA DE EMISI[ÓO]N)\s*[:\t\s]*([^\n]+)',
            r'emisi[^\n]*?([0-9]{1,2}[A-Z]{3}[0-9]{2,4})',
            r'\bEMITIDO\s+EL\b\s*[:\s]*([A-Z0-9 ]+)'
        ])

        airline = self.extract_field(text, [
            r'(?:Issuing Airline|AEROLÍNEA EMISORA|Aerol[íi]nea Emisora)\s*[:\t\s]*([^\n]+(?:\n\s*[^\n]+)?)'
        ])
        airline = re.sub(r'[,/].*$', '', airline).strip()
        
        agent = self.extract_field(text, [
            r'(?:Issuing Agent|AGENTE EMISOR|Agente Emisor)\s*[:\t\s]*([^\n]+)'
        ])
        
        iata = self.extract_field(text, [
            r'(?:IATA Number|IATA|N[úuú]mero IATA|NÚMERO IATA|NMERO IATA)\s*[:\t\s]*([0-9]+)',
            r'(?:Issuing Agent|AGENTE EMISOR|Agente Emisor)\s*[:\t\s]*[^\n]+\n\s*([0-9]{8})',
        ])
        
        # 4. Extraer Vuelos
        flights = self._parse_flights(text, airline_locator)
        
        airline_normalized_header = self.normalize_airline_name(airline, ticket_number=ticket_number)
        if airline_normalized_header and airline_normalized_header != 'Aerolínea no identificada':
            for f in flights:
                if not f.get('aerolinea') or f.get('aerolinea') == 'Aerolínea no identificada':
                    f['aerolinea'] = airline_normalized_header
        
        # 5. Extraer Tarifas
        fare_raw = self.extract_field(text, [
            r'(?<!Base de )\bTarifa\s+(?!total|Total|TOTAL)([A-Z]{3}\s*[0-9,.]+)',
            r'(?<!Base de )\bTarifa\s+USD\s+([0-9,.]+)',
            r'\bFare\s+(?!Total|total)([A-Z]{3}\s*[0-9,.]+)',
            r'\bFARE\s+(?!TOTAL)([A-Z]{3}\s*[0-9,.]+)'
        ])
        
        total_raw = self.extract_field(text, [
            r'(?<!Base de )\bTarifa\s+total\s+([A-Z]{3}\s*[0-9,.]+)',
            r'\bTotal\s+([A-Z]{3}\s*[0-9,.]+)',
            r'\bTOTAL\s*[:\s]*([A-Z]{3}\s*[0-9,.]+)',
            r'\bTARIFA\s+TOTAL\s*[:\s]*([A-Z]{3}\s*[0-9,.]+)'
        ])
        
        fare_currency, fare_amount = self.extract_currency_amount(fare_raw)
        total_currency, total_amount = self.extract_currency_amount(total_raw)
        
        # Detección de remisión por montos (Neto > Total)
        if fare_amount and total_amount:
            try:
                if float(str(fare_amount)) > float(str(total_amount)):
                    es_remision = True
                    logger.info("🎯 Detectada remisión por montos en Sabre.")
            except: pass

        tax_amount = "0.00"
        taxes = []
        if fare_amount and total_amount:
            try:
                f_val = float(str(fare_amount))
                t_val = float(str(total_amount))
                if t_val > f_val:
                    tax_val = t_val - f_val
                    tax_amount = f"{tax_val:.2f}"
                    taxes.append({'codigo': 'TAX', 'monto': tax_amount, 'moneda': total_currency})
            except: pass

        issue_date_iso = self.normalize_date(issue_date)

        return ParsedTicketData(
            source_system='SABRE',
            pnr=pnr,
            ticket_number=ticket_number,
            passenger_name=passenger_name,
            passenger_document=document_id,
            issue_date=issue_date_iso or issue_date,
            es_remision=es_remision,
            flights=flights,
            fares={
                'fare_currency': fare_currency,
                'fare_amount': str(fare_amount) if fare_amount else None,
                'total_currency': total_currency,
                'total_amount': str(total_amount) if total_amount else None,
                'tax_amount': tax_amount,
                'taxes': taxes
            },
            agency={
                'name': agent,
                'iata': iata,
                'numero_iata': iata
            },
            raw_data={
                'solo_nombre_pasajero': solo_nombre_pasajero,
                'reserva': {
                    'codigo_reservacion': pnr,
                    'numero_boleto': ticket_number,
                    'fecha_emision': issue_date,
                    'aerolinea_emisora': airline,
                    'agente_emisor': {
                         'nombre': agent,
                         'numero_iata': iata
                    }
                }
            }
        )

    def _parse_flights(self, text: str, airline_locator: str = None) -> List[Dict[str, Any]]:
        """Extrae información de vuelos del texto (Lógica robusta)"""
        flights = []
        # Normalizar espacios para evitar problemas de detección
        text_norm = re.sub(r' +', ' ', text)
        # Build a time pool PER SEGMENT, not globally
        # We'll use a local time find inside each block instead of a global list
        
        # Intentar detectar la sección de vuelos con múltiples posibles cabeceras
        headers = [
            r'Información [Dd]e Vuelo', r'Flight Information', r'Flight Details', 
            r'Airline Reservation Code', r'Detalles del vuelo'
        ]
        footers = [
            r'Detalles [Dd]e Pago', r'Payment Details', r'Aviso:', r'Notice:', 
            r'Información [Gg]eneral', r'Baggage Details'
        ]
        
        vuelo_section_match = re.search(
            f"(?:{'|'.join(headers)})(.*?)(?:{'|'.join(footers)}|$)", 
            text, re.DOTALL | re.IGNORECASE
        )
        
        if vuelo_section_match:
            vuelo_text = vuelo_section_match.group(1)
        else:
            # Fallback: Usar todo el texto si la sección no se identifica, 
            # pero filtrar bloques ruidosos conocidos
            logger.info("Sabre: No se identificó sección de vuelos clara. Usando fallback de texto completo.")
            vuelo_text = text
            
        vuelo_text = re.sub(r'(?:No válido|Not valid) (?:antes|después) del.*?\n', '', vuelo_text, flags=re.IGNORECASE)
        vuelo_text = re.sub(r'Est\. [Ee]mission.*?\n', '', vuelo_text, flags=re.IGNORECASE)
        vuelo_text = re.sub(r'.*?KG CO2.*?\n', '', vuelo_text, flags=re.IGNORECASE)
        
        # Dividir por marcadores de segmento
        # 1. Por fechas (Salida: DD MMM YY)
        # 2. Por "Operado por"
        # 3. Por códigos de reserva de aerolínea
        flight_blocks = re.split(
            r'(?:\n|^)\s*(?:Salida:|Departure:)?\s*(\d{1,2}\s*[a-zA-Z]{3,}\s*\d{2,4})', 
            vuelo_text, flags=re.IGNORECASE
        )
        
        processed_blocks = []
        if len(flight_blocks) > 1:
            # La división por regex de captura deja la fecha como un elemento y el resto como otro
            for i in range(1, len(flight_blocks), 2):
                date_part = flight_blocks[i]
                content_part = flight_blocks[i+1] if i+1 < len(flight_blocks) else ""
                processed_blocks.append(f"{date_part} {content_part}")
        else:
            # Si no hay fechas claras, intentar por "Preparado para" o "Operado por"
            processed_blocks = re.split(r'(?:Preparado para|Prepared For|Operado por|Operated by)', vuelo_text, flags=re.IGNORECASE)

        valid_blocks = []
        for block in processed_blocks:
            block = block.strip()
            # Un bloque válido debe tener al menos un número de vuelo potencial (Carrier + Nros)
            if not block or not re.search(r'\b[A-Z0-9]{2,3}\s?\d{1,4}[A-Z]?\b', block): continue
            valid_blocks.append(block)

        for block in valid_blocks:
            flight = {}
            lines = [line.strip() for line in block.splitlines() if line.strip()]
            for i, line in enumerate(lines):
                match = re.search(r'\b([A-Z0-9]{2}\s*\d{1,4})\b', line)
                if match:
                    flight['numero_vuelo'] = match.group(1).replace(' ', '')
                    airline_parts = []
                    for j in range(i - 1, max(-1, i - 3), -1):
                        prev_line = lines[j]
                        if re.search(r'\d{2}\s+\w{3}\s+\d{2}', prev_line) or ',' in prev_line or re.search(r'^[A-Z\s]{3,}$', prev_line):
                            break
                        airline_parts.insert(0, prev_line)
                    if airline_parts:
                        flight['aerolinea'] = self.normalize_airline_name(' '.join(airline_parts), flight.get('numero_vuelo'))
                    if not flight.get('aerolinea'):
                        flight['aerolinea'] = self.normalize_airline_name("", flight.get('numero_vuelo'))
                    break
            
            if not flight.get('numero_vuelo'): continue
            
            date_match = re.search(r'(\d{1,2}\s*\w{3}\s*\d{2,4})', block)
            if date_match: flight['fecha_salida'] = date_match.group(1)
            
            # Extract times LOCAL to this block (prevents mixing between segments)
            block_times = re.findall(r'\b(\d{1,2}:\d{2})\b', block)
            if len(block_times) >= 1: flight['hora_salida'] = block_times[0]
            if len(block_times) >= 2: flight['hora_llegada'] = block_times[1]
            
            # Origen / Destino - Sabre format: "AIRLINE_SEGMENT CITY_ORIGIN, COUNTRY CITY_DEST, COUNTRY"
            # The raw line looks like: "AEROVIAS DEL MEDELLIN, COLOMBIA BOGOTA, COLOMBIA"
            # We must extract the LAST word before the comma as the city for origin,
            # and also strip country names from destination.
            cities = re.findall(r'\b([A-Z\xc1\xc9\xcd\xd3\xda\xd1\u00c0-\u00ff][A-Z\xc1\xc9\xcd\xd3\xda\xd1\u00c0-\u00ff\s]{2,}?),', block)
            if len(cities) >= 2:
                raw_origin = self.clean_text(cities[0])  # e.g. "AEROVIAS DEL MEDELLIN"
                raw_dest = self.clean_text(cities[1])    # e.g. "COLOMBIA BOGOTA"

                # Strip airline-name-like prefixes from origin: take only the last word
                # e.g. "AEROVIAS DEL MEDELLIN" -> "MEDELLIN"
                origin_words = raw_origin.split()
                city_origin = origin_words[-1] if origin_words else raw_origin

                # Strip leading country name from destination: take only the last word
                # e.g. "COLOMBIA BOGOTA" -> "BOGOTA"
                dest_words = raw_dest.split()
                city_dest = dest_words[-1] if dest_words else raw_dest

                flight['origen'] = {'ciudad': city_origin, 'pais': None}
                flight['destino'] = {'ciudad': city_dest, 'pais': None}
            
            # Airline locator per-segment
            if airline_locator and airline_locator != 'No encontrado':
                flight['localizador_aerolinea'] = airline_locator
            
            bag_match = re.search(r'(?:Límite de equipaje|Baggage Allowance|Equipaje)[:\s]*([0-9]+\s*[PK]G)', block, re.IGNORECASE)
            if bag_match: flight['equipaje'] = bag_match.group(1).replace(' ', '')
            
            flights.append(flight)

        return flights

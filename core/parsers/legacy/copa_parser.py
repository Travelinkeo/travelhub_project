import re
import quopri
import logging
from typing import Dict, Any, List
from .base_parser import BaseTicketParser, ParsedTicketData

logger = logging.getLogger(__name__)


class CopaParser(BaseTicketParser):
    """Parser para boletos de Copa Airlines (sistema SPRK) - Extracción completa desde HTML"""
    
    def can_parse(self, text: str) -> bool:
        text_upper = text.upper()
        
        # Marcadores específicos de COPA SPRK
        has_copa = 'COPA AIRLINES' in text_upper
        has_locator = 'RECORD LOCATOR' in text_upper or 'LOCALIZADOR' in text_upper
        has_itinerary = 'ITINERARY' in text_upper or 'ITINERARIO' in text_upper
        
        # Evitar capturar boletos de GDS (Sabre) que sean de Copa
        is_sabre = 'RECIBO DE PASAJE ELECTRÓNICO' in text_upper or 'ETICKET RECEIPT' in text_upper
        
        return (has_copa and (has_locator or has_itinerary)) and not is_sabre
    
    def parse(self, text: str, html_text: str = "") -> ParsedTicketData:
        # Decodificar quoted-printable si es necesario
        decoded_text = self._decode_quoted_printable(text)
        
        # Extraer datos usando regex simple
        pnr = self._extract_pnr(decoded_text)
        airline_pnr = self._extract_airline_pnr(decoded_text)
        ticket_number = self._extract_ticket_number(decoded_text)
        issue_date = self._extract_issue_date(decoded_text)
        passenger_data = self._extract_passenger(decoded_text)
        agency_data = self._extract_agency(decoded_text)
        flights = self._extract_flights(decoded_text)
        
        return ParsedTicketData(
            source_system='COPA_SPRK',
            pnr=pnr,
            ticket_number=ticket_number,
            passenger_name=passenger_data.get('nombre_completo', 'No encontrado'),
            issue_date=issue_date,
            flights=flights,
            fares=self._extract_amounts(decoded_text),
            agency=agency_data,
            raw_data={
                'pasajero': passenger_data,
                'vuelos': flights,
                'fecha_creacion': issue_date,
                'agencia': agency_data,
                'agencia_iata': agency_data.get('iata', 'N/A'),
                'localizador_aerolinea': airline_pnr
            }
        )
    
    def _decode_quoted_printable(self, text: str) -> str:
        """Decodifica texto quoted-printable y limpia entidades HTML comunes"""
        try:
            decoded = quopri.decodestring(text.encode()).decode('utf-8', errors='ignore')
            # Limpiar entidades HTML que rompen los regex
            decoded = decoded.replace('&nbsp;', ' ')
            decoded = decoded.replace('&amp;', '&')
            return decoded
        except Exception as e:
            logger.warning(f"⚠️ Error decodificando quoted-printable: {e}")
            return text
    
    def _extract_pnr(self, text: str) -> str:
        """Extrae el PNR/Record Locator del sistema SPRK"""
        patterns = [
            r'Itinerary for Record Locator\s+<b>([A-Z0-9]{6})</b>',
            r'Itinerary for Record Locator\s+([A-Z0-9]{6})',
            r'Itinerario para localizador de reserva\s+<b>([A-Z0-9]{6})</b>',
            r'Itinerario para localizador de reserva\s+([A-Z0-9]{6})',
            r'Record Locator\s*[:\.]?\s*([A-Z0-9]{6})',
            r'Localizador de reserva\s*[:\.]?\s*([A-Z0-9]{6})'
        ]
        return self.extract_field(text, patterns)

    def _extract_airline_pnr(self, text: str) -> str:
        """Extrae el Record Locator de la aerolínea (Copa Airlines Record Locator)"""
        patterns = [
            r'Copa Airlines Record Locator\s+([A-Z0-9]{6})',
            r'Localizador de reserva de Copa Airlines\s+([A-Z0-9]{6})',
            r'Copa Airlines Localizador de reserva\s*\n*\s*([A-Z0-9]{6})', # Multiline support
            r'Copa Loc:\s*([A-Z0-9]{6})'
        ]
        return self.extract_field(text, patterns, default='N/A')
    
    def _extract_ticket_number(self, text: str) -> str:
        """Extrae el número de boleto electrónico (Document Number)"""
        # Patrón 1: Electronic Ticket       2307405222802   15JAN26
        patterns = [
            r'Electronic Ticket\s+(\d{13})',
            r'Boleto Electrónico\s+(\d{13})',
            r'Electronic Ticket.*?(\d{13})',
            r'Boleto Electrónico.*?(\d{13})',
            r'Document Number\s+(\d{13})',
            r'Número de Documento\s+(\d{13})'
        ]
        
        # Estrategia 2: Búsqueda Fuzzy (Prefijo Copa 230 + 10 dígitos)
        fuzzy_match = re.search(r'(?<!\d)(230\d{10})(?!\d)', text)
        if fuzzy_match:
            return fuzzy_match.group(1)
            
        return self.extract_field(text, patterns)
    
    def _extract_issue_date(self, text: str) -> str:
        """Extrae la fecha de emisión (Issuance Date)"""
        # Patrón complejo porque la fecha suele estar cerca del boleto
        
        # 1. Búsqueda directa con etiqueta
        direct_date = self.extract_field(text, [
            r'Issue Date\s*[:]?\s*(\d{2}[A-Z]{3}\d{2,4})',
            r'Fecha de Emisi[oó]n\s*[:]?\s*(\d{2}[A-Z]{3}[\d\.]{2,5})', # 04FEB.26, con acento opcional
            r'Fecha de emisi[oó]n\s*\n*\s*(\d{2}[A-Z]{3}[\d\.]{2,5})', # Multiline con punto y acento opcional
            r'Date of Issue\s*[:]?\s*(\d{2}[A-Z]{3}\d{2,4})'
        ])
        if direct_date != 'No encontrado':
            # Limpiar punto si existe (04FEB.26 -> 04FEB26)
            return direct_date.replace('.', '')

        # 2. Búsqueda contextual cerca del boleto (Regex Manual)
        # Electronic Ticket       2307405222802   15JAN26
        match = re.search(r'(?:Electronic Ticket|Boleto Electrónico)\s+\d{13}\s+(\d{2}[A-Z]{3}[\d\.]{2,4})', text, re.IGNORECASE)
        if match: return match.group(1).replace('.', '')
            
        # 3. HTML Table Context
        match = re.search(r'\d{13}.*?>\s*(\d{2}[A-Z]{3}[\d\.]{2,4})\s*<', text, re.IGNORECASE | re.DOTALL)
        if match: return match.group(1).replace('.', '')
            
        return 'No encontrado'
    
    def _extract_passenger(self, text: str) -> Dict[str, str]:
        """Extrae información del pasajero eliminando ruidos comunes"""
        # Buscar: PM E Y S YEISBENTH GONZALEZ CAMACHO (ADT)
        match = re.search(r'([A-ZÁÉÍÓÚÑ(0-9.)\s]+?)\s*\(ADT\)', text)
        if match:
            raw_name = match.group(1).strip()
            
            # Limpieza de prefijos ruidosos (PM, 1.1, etc.)
            # A veces aparece PM E Y S (Probablemente Passenger Main...)
            clean_name = re.sub(r'^(?:PM|1\.\d|2\.\d|3\.\d|[A-Z])\s+E\s+Y\s+S\s+', '', raw_name, flags=re.IGNORECASE)
            clean_name = re.sub(r'^(?:PM|1\.\d|2\.\d|[A-Z])\s+', '', clean_name, flags=re.IGNORECASE).strip()
            
            # Sanitización de caracteres especiales residuales
            clean_name = re.sub(r'\s+', ' ', clean_name)
            
            return {
                'nombre_completo': clean_name or raw_name,
                'tipo': 'ADT'
            }
        
        # Fallback: Usar extractor robusto de la clase base
        p_name = self.extract_passenger_name_robust(text)
        return {'nombre_completo': p_name, 'tipo': 'ADT'}
    
    def _extract_agency(self, text: str) -> Dict[str, str]:
        """Extrae información de la agencia (IATA)"""
        # Grupo Soporte Global INC     IATA: 10617390
        # Puede venir en varias líneas o formatos, buscamos el ancla "IATA:"
        
        # Estrategia 1: Label Específico Spanish - Muy flexible
        match_esp = re.search(r'IATA de la agencia.*?(\d{7,10})', text, re.IGNORECASE | re.DOTALL)
        if match_esp:
             return {'nombre': 'Agencia IATA', 'iata': match_esp.group(1)}

        match = re.search(r'([A-ZÁÉÍÓÚÑ0-9\s\.]+?)\s+IATA:\s*(\d+)', text)
        if match:
            # Limpiar nombre (a veces captura demasiado texto previo)
            raw_name = match.group(1).strip()
            # Tomar ultimas 5-6 palabras si es muy largo
            tokens = raw_name.split()
            if len(tokens) > 6:
                name = ' '.join(tokens[-6:])
            else:
                name = raw_name
                
            return {
                'nombre': name,
                'iata': match.group(2)
            }
            
        # Estrategia 2: Búsqueda IATA suelta
        match_fuzzy = re.search(r'IATA\s*[:\.]?\s*(\d{7,10})', text, re.IGNORECASE)
        if match_fuzzy:
             return {'nombre': 'Agencia IATA', 'iata': match_fuzzy.group(1)}
        
        return {'nombre': 'No encontrado', 'iata': 'No encontrado'}
        return {'nombre': 'No encontrado', 'iata': 'No encontrado'}

    def _extract_amounts(self, text: str) -> Dict[str, Any]:
        """Extrae información financiera (Total, Impuestos)"""
        # Formato: 
        # Total Amount: USD 123.45  o  Total: USD 123.45
        # Taxes: USD 45.00
        
        amounts = {}
        
        # Buscar Total
        patterns_total = [
            r'Total Amount\s*[:]?\s*([A-Z]{3})\s*([\d,.]+)',
            r'Total\s*[:]?\s*([A-Z]{3})\s*([\d,.]+)',
            r'Monto Total\s*[:]?\s*([A-Z]{3})\s*([\d,.]+)',
            r'Grand Total\s*[:]?\s*([A-Z]{3})\s*([\d,.]+)'
        ]
        
        currency = None
        total = None
        
        for p in patterns_total:
            match = re.search(p, text, re.IGNORECASE)
            if match:
                currency = match.group(1)
                total_str = match.group(2).replace(',', '') # Asumimos format 1,234.56
                try:
                    total = str(Decimal(total_str))
                    break
                except Exception as e:
                    logger.warning(f"⚠️ Error al convertir total '{total_str}': {e}")
        
        if total:
            amounts['total_amount'] = total
            amounts['currency'] = currency
            amounts['total'] = total # Legacy
            amounts['total_currency'] = currency
            
        return amounts

    def _extract_flights(self, text: str) -> List[Dict[str, Any]]:
        """Extrae información de vuelos - Formato compatible con ticket_parser.py"""
        flights = []
        
        # Normalización profunda para búsqueda multilínea
        text_clean = text.replace('\n', ' ').replace('\r', ' ')
        text_clean = re.sub(r'\s+', ' ', text_clean)
        
        # Estrategia 1: Detección por código CM o Copa Airlines
        # Buscamos números de vuelo precedidos por Copa Airlines o CM
        candidates = list(re.finditer(r'(?:Copa Airlines|CM)\s+(\d{1,4})', text_clean, re.IGNORECASE))
        
        logger.info(f"🔍 CopaParser detectó {len(candidates)} candidatos de vuelos.")
        
        for m in candidates:
            f_num = m.group(1)
            move_pos = m.end()
            # Aumentamos el chunk a 1200 para capturar itinerarios largos con mucho HTML residual
            chunk = text_clean[move_pos:move_pos + 1200]
            
            # Regex robustecido para el segmento
            # Soporta ciudades sin país binario (ej: MADRID) o con país largo (ej: COLOMBIA)
            # Busca Departure City ... [Hora] ... Arrival City ... [Hora]
            seg_regex = re.compile(
                r'(.*?),\s*([A-Z]{2}|[A-Z][a-z]+).*?(\d{2}:\d{2}\s*[AP]M)\s+(.*?),\s*([A-Z]{2}|[A-Z][a-z]+).*?(\d{2}:\d{2}\s*[AP]M)',
                re.IGNORECASE
            )
            
            seg_match = seg_regex.search(chunk)
            if seg_match:
                # Extraer fecha (ej: 15ABR) buscando antes o después del número de vuelo en el chunk
                # Copa suele poner la fecha cerca del número de vuelo o antes de la hora
                date_match = re.search(r'(\d{1,2}[A-Z]{3})', chunk[:seg_match.start(3)], re.IGNORECASE)
                f_date = date_match.group(1) if date_match else "N/A"
                
                # Evitar duplicados por PNR que repite info
                flight_key = f"{f_num}-{seg_match.group(1).strip()}-{f_date.upper()}"
                if any(f"{f['numero_vuelo']}-{f['origen']}-{f['fecha_salida']}" == flight_key for f in flights):
                    continue

                flights.append({
                    'aerolinea': 'Copa Airlines',
                    'numero_vuelo': f_num,
                    'origen': seg_match.group(1).strip(),
                    'fecha_salida': f_date.upper(),
                    'hora_salida': seg_match.group(3).strip(),
                    'destino': seg_match.group(4).strip(),
                    'hora_llegada': seg_match.group(6).strip(),
                    'cabina': 'Económica',
                    'clase': 'L'
                })

        return flights

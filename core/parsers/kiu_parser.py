"""Parser refactorizado para boletos KIU (Versión Fiscal Venezuela)"""
import re
from typing import Dict, Any, Tuple, Optional, List
from decimal import Decimal, InvalidOperation
from .base_parser import BaseTicketParser, ParsedTicketData
from core.parsing_utils import _inferir_fecha_llegada

class KIUParser(BaseTicketParser):
    """Parser para boletos del sistema KIU"""

    def can_parse(self, text: str) -> bool:
        """Detecta si es un boleto KIU"""
        text_upper = text.upper()
        return 'KIUSYS.COM' in text_upper or \
               'PASSENGER ITINERARY RECEIPT' in text_upper or \
               ('ISSUE AGENT/AGENTE EMISOR' in text_upper and 'FROM/TO' in text_upper)

    def parse(self, text: str, html_text: str = "") -> ParsedTicketData:
        """Parsea boleto KIU"""
        
        # 0. Limpieza PREVIA: Eliminar metadatos HTML si se colaron en texto plano
        # (El usuario reportó que le llegan tags <B> que rompen el regex)
        # Reemplazamos tags por espacio para evitar palabras pegadas
        text = re.sub(r'<[^>]+>', ' ', text)
        
        # 1. Intentar parsear como líneas crudas primero si no parece un boleto completo
        raw_kiu_pattern = r'^\s*\d+\s+[A-Z0-9]{2}\d+\s+[A-Z]\s+\d{2}[A-Z]{3}'
        if re.search(raw_kiu_pattern, text, re.MULTILINE):
             return self._parse_raw_kiu_lines(text)

        # 2. Parseo estándar de boleto KIU
        passenger_name = self._extract_passenger_name(text)
        pnr = self._extract_pnr(text)
        ticket_number = self._extract_ticket_number(text)
        issue_date = self._extract_issue_date(text)
        airline_name = self._extract_airline(text, ticket_number=ticket_number)
        
        # Extraer montos
        amounts = self._extract_amounts(text)
        
        
        # Extraer vuelos (lógica simplificada para este ejemplo, se puede expandir)
        flights = self._extract_flights(text, html_text, issue_date=issue_date)
        
        # HEURÍSTICA DE REPARACIÓN DE EMPLEADOS VIAJEROS
        # Si el nombre es 'S BOLETO NRO' (error típico), intentar buscar otro nombre
        # o marcar como revisión.
        if "BOLETO NRO" in passenger_name:
             passenger_name = "PENDIENTE / REVISAR" # Fallback

        # Calcular SOLO_NOMBRE (Primer nombre) para el saludo
        solo_nombre = passenger_name
        if '/' in passenger_name:
            try:
                parts = passenger_name.split('/')
                if len(parts) > 1:
                    solo_nombre = parts[1].strip().split()[0] # Tomar primer token del nombre
            except: pass

        return ParsedTicketData(
            source_system="KIU",
            pnr=pnr,
            passenger_name=passenger_name,
            ticket_number=ticket_number,
            issue_date=issue_date,
            agency={
                "iata": self._extract_agency_iata(text),
                "nombre": self._extract_agency_name(text),
                "direccion": self._extract_agency_address(text)
            },
            flights=flights,
            fares=amounts,
            raw_data={
                "ItinerarioFinalLimpio": self._extract_itinerary_text(text),
                "SOLO_NOMBRE_PASAJERO": solo_nombre, 
                "passenger_name": passenger_name # Redundancia para seguridad
            },
            passenger_document=self._extract_foid(text)
        )

    def _extract_foid(self, text: str) -> str:
        """Extrae el FOID (Documento de Identidad)"""
        return self.extract_field(text, [
            r'FOID\s*[:\s]*([A-Z0-9-]+)',
            r'DOCUMENTO\s*[:\s]*([A-Z0-9-]+)',
            r'ID\s*[:\s]*([0-9-]{6,})',
            r'CEDULA\s*[:\s]*([VNEJP]-?[0-9.]+)'
        ])

    def _parse_raw_kiu_lines(self, text: str) -> ParsedTicketData:

        """Parsea líneas de itinerario crudo de KIU."""
        flights = []
        lines = text.splitlines()
        # Regex: 1 5R300 S 30NOV SU CCSPMV HK1 0800 0840
        pattern = r'^\s*\d+\s+([A-Z0-9]{2})(\d+)\s+([A-Z])\s+(\d{2}[A-Z]{3})\s+[A-Z]{2}\s+([A-Z]{3})([A-Z]{3})\s+[A-Z0-9]+\s+(\d{4})\s+(\d{4})'
        
        for line in lines:
            match = re.search(pattern, line)
            if match:
                airline_code = match.group(1)
                flight_num = match.group(2)
                clase = match.group(3)
                date_str = match.group(4)
                origin = match.group(5)
                dest = match.group(6)
                dep_time = match.group(7)
                arr_time = match.group(8)
                
                # Formatear hora (0800 -> 08:00)
                dep_time_fmt = f"{dep_time[:2]}:{dep_time[2:]}"
                arr_time_fmt = f"{arr_time[:2]}:{arr_time[2:]}"
                
                flights.append({
                    "aerolinea": airline_code,
                    "numero_vuelo": flight_num,
                    "clase": clase,
                    "fecha_salida": date_str,
                    "origen": origin,
                    "destino": dest,
                    "hora_salida": dep_time_fmt,
                    "hora_llegada": arr_time_fmt,
                    "equipaje": "N/A" # No disponible en línea cruda
                })
                
        return ParsedTicketData(
            source_system="KIU",
            pnr="MANUAL",
            passenger_name="MANUAL",
            ticket_number="N/A",
            issue_date="N/A",
            flights=flights,
            raw_data={"ItinerarioFinalLimpio": text}
        )

    def _heuristic_extract_total_and_currency(self, text: str) -> Tuple[Decimal, str]:
        # 1. Determinar Moneda Globalmente
        moneda = 'USD'
        if re.search(r'\b(VES|BS\.?|BOLIVARES)\b', text, re.IGNORECASE):
            moneda = 'VES'
        elif re.search(r'\b(EUR|EUROS)\b', text, re.IGNORECASE):
            moneda = 'EUR'

        # 2. Buscar TODOS los posibles montos (patrón: dígitos + punto/coma + 2 decimales)
        # Excluimos años (2025) y números de boleto largos
        regex_montos = r'\b\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})\b|\b\d+[.,]\d{2}\b'
        
        candidatos = re.findall(regex_montos, text)
        valores = []
        
        for c in candidatos:
            try:
                # Limpieza y normalización de montos
                clean_c = c.replace(' ', '')
                # Detectar formato: 1.234,56 (EU/VE) vs 1,234.56 (US)
                if ',' in clean_c and '.' in clean_c:
                    if clean_c.rfind(',') > clean_c.rfind('.'): # Caso 1.234,56
                        clean_c = clean_c.replace('.', '').replace(',', '.')
                    else: # Caso 1,234.56
                        clean_c = clean_c.replace(',', '')
                elif ',' in clean_c:
                     # Caso 1234,56
                     clean_c = clean_c.replace(',', '.')
                
                valor = float(clean_c)
                
                # Filtros de Seguridad (Heurística)
                # Ignoramos años (ej: 2024, 2025) si aparecen como montos sueltos,
                # pero 2025.00 sí podría ser un monto.
                # Rango de validez: 10 < valor < 100,000,000
                if 10 < valor < 100000000: 
                    valores.append(Decimal(str(valor)))
            except:
                continue
        
        # El total a pagar suele ser el monto numérico más alto en el documento
        monto_total = max(valores) if valores else Decimal("0.00")
        
        return monto_total, moneda

    def _extract_amounts(self, text: str) -> Dict[str, Any]:
        # 1. Estrategia Robusta: "Max Number Strategy"
        heur_total, heur_currency = self._heuristic_extract_total_and_currency(text)
        
        # 2. Extracción de Base e Impuestos (Intentamos mantener desglose si es posible)
        # Usamos regex específicos solo para 'Fare' o 'Base'
        raw_base = self.extract_field(text, [
            r'(?:AIR FARE|TARIFA|FARE)\s*[:\s]*([A-Z]{3}\s*[0-9,.]+)', 
            r'NETO\s*[:\s]*([A-Z]{3}\s*[0-9,.]+)'
        ])
        base_curr, base_amt = self.extract_currency_amount(raw_base)
        
        # Si la heurística falló (0.00), intentamos usar lo específico
        total_amt = heur_total
        currency = heur_currency
        
        if total_amt == 0 and base_amt:
             total_amt = base_amt # Fallback parcial
             currency = base_curr or currency

        # 3. Cálculo de Impuestos (Diferencia)
        tax_amt = Decimal("0.00")
        if total_amt > 0 and base_amt and total_amt >= base_amt:
            tax_amt = total_amt - base_amt
        elif total_amt > 0 and not base_amt:
            # Si no hay base, asumimos que todo es base+impuestos, 
            # pero para efectos contables podríamos estimar o dejar base=total (neto)
            base_amt = total_amt 
        
        # 4. Búsqueda de IVA (YN) para desglose
        iva_amt = Decimal("0.00")
        iva_match = re.search(r'([0-9]{1,5}(?:[.,][0-9]{2})?)\s*(?:YN)', text)
        if iva_match:
            try:
                raw_iva = iva_match.group(1).replace(',','.') # Simple fix
                iva_amt = Decimal(raw_iva)
            except: pass

        other_taxes = Decimal("0.00")
        if tax_amt >= iva_amt:
            other_taxes = tax_amt - iva_amt
        else:
            # Si la diferencia es menor al IVA detectado, algo anda mal, priorizamos el Total Heurístico
            tax_amt = iva_amt # Asumimos al menos el IVA
            
        return {
            'currency': currency,
            'fare_amount': str(base_amt) if base_amt else "0.00",
            'total_amount': str(total_amt),
            'tax_details': {
                'total_taxes': str(tax_amt),
                'iva_yn': str(iva_amt),
                'other_taxes': str(other_taxes)
            }
        }

    def _extract_ticket_number(self, text: str) -> str:
        """Extrae el número de boleto"""
        patterns = [
            r'TICKET N[BR]O?\s*[:\s]*([0-9-]{8,})',
            r'TICKET NUMBER\s*[:\s]*([0-9-]{8,})',
            r'E-TICKET\s*[:\s]*([0-9-]{8,})',
            r'BOLETO\s*[:\s]*([0-9-]{8,})',
            r'\b(\d{3}-?\d{10})\b',  # Formato estándar XXX-XXXXXXXXXX
        ]
        return self.extract_field(text, patterns)
    
    def _extract_issue_date(self, text: str) -> str:
        """Extrae la fecha de emisión"""
        patterns = [
            r'(?:ISSUE DATE|FECHA DE EMISI[OÓ]N|DATE OF ISSUE)\s*[:\s]*(\d{1,2}\s+\w{3}\s+\d{2,4})',
            r'(?:ISSUED|EMITIDO)\s*[:\s]*(\d{1,2}\s+\w{3}\s+\d{2,4})',
            r'(?:ISSUE DATE|FECHA DE EMISI[OÓ]N)\s*[:\s]*\n\s*(\d{1,2}\s+\w{3}\s+\d{2,4})', # Multiline explicitly
            r'(\d{2}[A-Z]{3}\d{2})',  # Formato compacto: 15JAN25
        ]
        return self.extract_field(text, patterns)
    
    def _extract_pnr(self, text: str) -> str:
        """Extrae el PNR con múltiples patrones"""
        # Patrón 1: C1/XXXXXX (formato más común en KIU)
        match = re.search(r"C1\s*/\s*([A-Z0-9]{6})", text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        
        # Patrón 2: BOOKING REF seguido del código
        booking_ref = self.extract_field(text, [
            r'BOOKING REF\.?\s*[:\s]*([A-Z0-9]{6})',
            r'BOOKING REFERENCE\s*[:\s]*([A-Z0-9]{6})',
            r'PNR\s*[:\s]*([A-Z0-9]{6})',
            r'LOCALIZADOR\s*[:\s]*([A-Z0-9]{6})'
        ])
        
        if booking_ref != 'No encontrado':
            # Si encontró algo, extraer solo el código de 6 caracteres
            match = re.search(r'\b([A-Z0-9]{6})\b', booking_ref)
            if match:
                return match.group(1)
            return booking_ref
        
        return 'No encontrado'
    
    
    def _extract_passenger_name(self, text: str) -> str:
        """Extrae el nombre del pasajero usando la estrategia robusta centralizada"""
        return self.extract_passenger_name_robust(text)
    
    
    def _extract_agency_iata(self, text: str) -> str:
        return self.extract_field(text, [r'IATA\s*[:\s]*([0-9]{8})'])

    def _extract_agency_name(self, text: str) -> str:
        # PRIORIDAD: Capturar exactamente lo que sigue a ISSUE AGENT / AGENTE EMISOR
        # El usuario indica que este es el código de la agencia (ej: BLA005RSJ)
        # y NO la aerolínea. Usamos lógica de main (3).py.
        raw_agent = self.extract_field(text, [
            r'ISSUE AGENT/AGENTE EMISOR\s*[:\s]*(.+)', 
            r'ISSUE AGENT\s*[:\s]*(.+)',
            r'AGENTE EMISOR\s*[:\s]*(.+)',
            r'OFFICE ID\s*[:\s]*(.+)'
        ])
        
        if raw_agent and raw_agent != 'No encontrado':
             # Limpieza: El usuario indica que es un código de 8-9 caracteres (Office ID)
             # Ej: MIAO08217
             # A veces el regex captura "MIAO08217 DORAL FLORIDA..."
             # Tomamos la primera palabra y verificamos si parece un ID.
             first_word = raw_agent.split()[0].replace(":", "").strip()
             if 6 <= len(first_word) <= 12 and re.match(r'^[A-Z0-9]+$', first_word):
                 return first_word
             
             # Si no parece código, devolvemos la línea limpia (fallback)
             return raw_agent.split('\n')[0].strip()

        return 'No encontrado'

    def _extract_agency_address(self, text: str) -> str:
        # Rutaca specifics
        if 'RUTACA' in text.upper():
             return 'AV JESUS SOTO SECTOR AEROPUERTO EDIF TALLER MARES, CIUDAD BOLIVAR, VE'
        
        # Extraer dirección pero DETENERSE ante keywords o salto de linea doble
        # Usamos un patrón que capture hasta encontrar keywords de fin de bloque
        raw_addr = self.extract_field(text, [
            r'ADDRESS/DIRECCI[OÓ]N\s*[:\s]*([^\n]+)', 
            r'ADDRESS\s*[:\s]*([^\n]+)',
            r'DIRECCI[OÓ]N\s*[:\s]*([^\n]+)',
            r'ADDRESS/DIRECCI[OÓ]N\s*[:\s]*\n\s*([^\n]+)' # Multiline explicit check
        ])

        if raw_addr == 'No encontrado':
             return raw_addr

        # Limpieza adicional por si la linea es muy larga o contiene basura
        stop_tokens = ['RIF', 'TICKET', 'NAME', 'TELEPHONE', 'MAIL', 'ISSUING']
        upper_addr = raw_addr.upper()
        
        cutoff = len(raw_addr)
        for token in stop_tokens:
            idx = upper_addr.find(token)
            if idx != -1:
                cutoff = min(cutoff, idx)
        
        return raw_addr[:cutoff].strip(" :-,.")

    def _extract_airline(self, text: str, ticket_number: str = None) -> str:
        """Extrae el nombre de la aerolínea con limpieza avanzada y normalización"""
        
        # 1. Extracción Cruda
        raw = self.extract_field(text, [
            r'ISSUING AIRLINE/LINEA AEREA EMISORA\s*[:\s]*([A-Z0-9 ,.&-]{3,})',
            r'ISSUING AIRLINE\s*[:\s]*([A-Z0-9 ,.&-]{3,})',
            r'LINEA AEREA EMISORA\s*[:\s]*([A-Z0-9 ,.&-]{3,})',
            r'LINEA AEREA EMISORA\s*[:\s]*\n\s*([A-Z0-9 ,.&-]{3,})', # Multiline explicit
            r'AEROLINEA\s*[:\s]*([A-Z0-9 ,.&-]{3,})'
        ])
        
        # 2. Normalización usando Base de Datos (Prioridad Placa -> IATA -> Nombre)
        # Usamos la función robusta que ya implementamos en BaseTicketParser/airline_utils
        normalized = self.normalize_airline_name(raw, ticket_number=ticket_number)
        
        if normalized and normalized != "Aerolínea no identificada":
            return normalized

        # 3. Fallbacks Heurísticos (solo si la normalización falló o devolvió nombre crudo sin match)
        upper_text = text.upper()
        if 'RUTACA' in upper_text: return 'RUTACA AIRLINES'
        if 'AVIOR' in upper_text: return 'AVIOR AIRLINES'
        if 'ESTELAR' in upper_text: return 'AEROLINEAS ESTELAR'
        if 'CONVIASA' in upper_text: return 'CONVIASA'
        if 'LASER' in upper_text: return 'LASER AIRLINES'
        if 'TURPIAL' in upper_text: return 'TURPIAL AIRLINES'
        if 'VENEZOLANA' in upper_text: return 'VENEZOLANA'
        
        # Limpieza final del raw si todo falla
        if raw != 'No encontrado':
             # Eliminar "AGENTE" y todo lo que viene después
            raw = re.sub(r'\s+AGENTE.*$', '', raw, flags=re.IGNORECASE)
            # Limpiar sufijos
            raw = re.sub(r'/[A-Z0-9]{2,3}\s*$', '', raw)
            return raw.strip()
            
        return "Aerolínea no identificada"

    def _extract_flights(self, text: str, html_text: str = "", issue_date: str = None) -> List[Dict[str, Any]]:
        """Extrae vuelos del itinerario KIU"""
        flights = []
        seen_flights = set()
        import logging
        from datetime import datetime
        logger = logging.getLogger(__name__)
        
        # Patrón ancla: VUELO + CLASE + FECHA (Ej: V01187 G 2FEB o ES 791 G 2FEB26)
        # Se permite espacio opcional en el número de vuelo (ej: "ES 791")
        # Fecha: \d{1,2}[A-Z]{3} captura dia y mes. Añadimos (?:\d{2})? para año opcional.
        anchor_pattern = r'([A-Z0-9]{2}\s?\d{3,4})\s+([A-Z])\s+(\d{1,2}[A-Z]{3}(?:\d{2})?)'
        
        # Intentar parsear el año de emisión para usarlo de base
        dt_issue = None
        current_year = datetime.now().year
        
        if issue_date:
            from dateutil import parser as date_parser
            try:
                # issue_date suele venir normalizado o crudo? 
                # _extract_issue_date devuelve string, tratemos de parsearlo
                dt_issue = date_parser.parse(issue_date, fuzzy=True)
                current_year = dt_issue.year
            except:
                pass

        lines = text.splitlines()
        for i, line in enumerate(lines):
            line = line.strip()
            if not line: continue
            
            # Buscar el ancla
            match = re.search(anchor_pattern, line)
            if match:
                logger.info(f"DEBUG: Found flight anchor in '{line}'")
                
                flight_num = match.group(1).replace(" ", "") # Normalizar quitando espacios internos
                clase = match.group(2)
                date_raw = match.group(3) # Ej: 02FEB o 02FEB26
                
                # Normalizar Fecha a YYYY-MM-DD
                # Usamos método interno para evitar problemas de importación con stale modules
                flight_date = self._parse_date_iso(date_raw, reference_date=dt_issue, base_year=current_year)
                
                # Lo que está ANTES del ancla es el Origen
                # match.start() es donde empieza el vuelo
                origin_raw = line[:match.start()].strip()
                
                # Lo que está DESPUÉS del ancla
                rest_raw = line[match.end():].strip()
                
                # Extraer horas del resto (Ej: 0850 0950 ...)
                # Buscamos dos bloques de 4 dígitos
                times_match = re.search(r'(\d{4})\s+(\d{4})', rest_raw)
                dep_fmt = "00:00"
                arr_fmt = "00:00"
                
                if times_match:
                    dep_time = times_match.group(1)
                    arr_time = times_match.group(2)
                    dep_fmt = f"{dep_time[:2]}:{dep_time[2:]}"
                    arr_fmt = f"{arr_time[:2]}:{arr_time[2:]}"
                
                # Aerolínea Normalizada por Código de Vuelo
                # Usamos el método de la clase base que ya consulta DB
                airline = self.normalize_airline_name(raw_name=None, flight_code=flight_num)
                
                # Si falló la normalización, intentar inferir del código IATA manual o default
                if airline == "Aerolínea no identificada":
                     code = flight_num[:2]
                     if code == 'V0': airline = 'CONVIASA'
                     elif code == '9V': airline = 'AVIOR AIRLINES'
                     elif code == 'ES': airline = 'AEROLINEAS ESTELAR'
                     elif code == 'VE': airline = 'RUTACA AIRLINES'
                     elif code == 'QL': airline = 'LASER AIRLINES'
                     elif code == 'L5': airline = 'LASER AIRLINES'
                     elif code == 'R7': airline = 'ASERCA'
                     elif code == 'Q6': airline = 'VIO'
                     elif code == 'G6': airline = 'GLOBAL AIRLINES'
                     else: airline = "Aerolínea desconocida (" + code + ")"

                # Equipaje (Formatos: 23K, 2PC, 2P, 1PC, NIL, etc)
                # (?i) para case-insensitive (nil/NIL)
                bag_match = re.search(r'(?i)(NIL|\d{1,2}K|\d{1,2}PC|\d{1,2}P)\b', rest_raw)
                
                if bag_match:
                    equipaje = bag_match.group(1).upper()
                    if equipaje == 'NIL':
                        equipaje = '0PC'
                else:
                    # Fallback para webs de Estelar, Rutaca, Avior que no imprimen equipaje
                    # Por defecto asumimos 1 pieza (23kg)
                    airline_upper = airline.upper()
                    if any(x in airline_upper for x in ['ESTELAR', 'RUTACA', 'AVIOR']):
                        equipaje = "1PC"
                    else:
                        equipaje = "N/A"
                
                # Destino: Buscar en la siguiente línea
                dest = "DESCONOCIDO"
                if i + 1 < len(lines):
                    next_line = lines[i+1].strip()
                    
                    # Limpieza agresiva de ruido (ej: "MADRID /CIERRE CHECKIN...")
                    # Cortar en /, *, o palabras clave que indican fin del nombre de ciudad
                    clean_dest = next_line
                    split_chars = ['/', '*', 'CIERRE', 'CHECKIN', 'REQUERIR', 'APIS', 'OPERADO', 'EQUIPAJE']
                    for char in split_chars:
                        if char in clean_dest:
                            clean_dest = clean_dest.split(char)[0]
                    
                    clean_dest = clean_dest.strip()
                    
                    # Validar formato de ciudad (letras, espacios, guiones, puntos)
                    # Permitir BOGOTA-EL DORADO (con guion)
                    if re.match(r'^[A-ZÁÉÍÓÚ \.-]+$', clean_dest) and len(clean_dest) >= 3:
                        if not any(kw in clean_dest for kw in ['NAME', 'PNR', 'TICKET', 'TOTAL']):
                            dest = clean_dest
                
                # Generar clave única para evitar duplicados (ej: si el PDF repite el itinerario)
                unique_key = f"{flight_num}-{date_raw}-{origin_raw}"
                
                # Verificar si ya existe este segmento
                if unique_key in seen_flights:
                    continue
                seen_flights.add(unique_key)
                
                flights.append({
                    "aerolinea": airline,
                    "numero_vuelo": flight_num,
                    "clase": clase,
                    "fecha_salida": flight_date, # Fecha ISO
                    "fecha_original": date_raw,
                    "origen": origin_raw,
                    "destino": dest,
                    "hora_salida": dep_fmt,
                    "hora_llegada": arr_fmt,
                    "equipaje": equipaje
                })

        return flights

    def _parse_date_iso(self, date_str: str, reference_date=None, base_year=None) -> str:
        """
        Versión interna de _parse_date_flexible para evitar problemas de importación.
        """
        import datetime as dt
        if not date_str: return ""
        date_upper = date_str.upper().strip()
        month_map = {'ENE': 'JAN', 'ABR': 'APR', 'AGO': 'AUG', 'DIC': 'DEC'}
        for es, en in month_map.items():
            date_upper = date_upper.replace(es, en)
            
        try:
            dt_obj = None
            if re.match(r'^\d{1,2}[A-Z]{3}\d{2}$', date_upper): # 02FEB26
                dt_obj = dt.datetime.strptime(date_upper, "%d%b%y")
            elif re.match(r'^\d{1,2}[A-Z]{3}\d{4}$', date_upper): # 02FEB2026
                dt_obj = dt.datetime.strptime(date_upper, "%d%b%Y")
            elif re.match(r'^\d{1,2}[A-Z]{3}$', date_upper): # 02FEB
                year = base_year or dt.now().year
                if reference_date: year = reference_date.year
                dt_obj = dt.datetime.strptime(date_upper + str(year), "%d%b%Y")
                
                # Ajuste de año nuevo
                if reference_date:
                    if (reference_date - dt_obj).days > 300: # Vuelo pasado (Ene) vs Emision Futuro (Dic)? No.
                        # Si emision es Dic 2025 y vuelo Ene 2025 (parseado), vuelo real es 2026.
                        # Diff = +330 dias aprox.
                        pass # No, dt_obj es Ene 2025. ref es Dic 2025.
                        # dt_obj < ref.
                    
                    # Logica simple:
                    # Si mes vuelo < mes emision Y diferencia > 6 meses, sumar 1 año.
                    if dt_obj.month < reference_date.month and (reference_date.month - dt_obj.month) > 6:
                        dt_obj = dt_obj.replace(year=year + 1)
            
            if dt_obj:
                return dt_obj.strftime("%Y-%m-%d")
        except:
            pass
        return date_str

    def _extract_itinerary_text(self, text: str) -> str:
        # Extraer bloque de itinerario
        start_pattern = r'(FROM/TO|DESDE/HACIA)[\s/]+(FLIGHT|VUELO)'
        end_keywords = ['ENDORSEMENTS', 'CONDICIONES', 'FARE CALC', 'TOUR CODE', 'PAYMENT', 'TOTAL']
        
        lines = text.splitlines()
        itinerary_content = []
        capturing = False
        
        for line in lines:
            if not capturing and re.search(start_pattern, line.upper()):
                capturing = True
                continue
            
            if capturing:
                if any(keyword in line.upper() for keyword in end_keywords):
                    break
                if line.strip():
                    itinerary_content.append(line.strip())
                    
        return '\n'.join(itinerary_content)
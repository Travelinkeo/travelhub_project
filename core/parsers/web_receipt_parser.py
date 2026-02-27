import logging
import re
from decimal import Decimal
from datetime import datetime
import datetime as mt # Alias
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional
from core.parsing_utils import _parse_currency_amount, _clean_value

logger = logging.getLogger(__name__)

class WebReceiptParser:
    """
    Parser especializado para "Recibos Web" (HTML) de aerolíneas venezolanas 
    (Estelar, Avior, Rutaca) que llegan por correo y a menudo contienen 
    múltiples pasajeros en un solo archivo (Manifiesto).
    """

    def can_parse(self, text: str) -> bool:
        """Determina si este parser puede procesar el texto dado."""
        text_upper = text.upper()
        
        # Avior (Inglés/Español/Mixed)
        if "AVIOR" in text_upper and ("RESERVA" in text_upper or "LOCALIZADOR" in text_upper or "PNR" in text_upper or "CONFIRMACION" in text_upper or "CONFIRMATION" in text_upper or "BOOKING" in text_upper):
             return True
        
        # Rutaca
        if "RUTACA AIRLINES" in text_upper or "TICKETS RUTACA" in text_upper:
             return True
             
        # Estelar
        if "ESTELAR" in text_upper and ("TICKETS ESTELAR" in text_upper or "TICKETS EMITIDOS" in text_upper):
             return True
             
        return False

    def _clean_money(self, value_str: str) -> Decimal:
        """Limpia strings de moneda (1.234,56 -> 1234.56)."""
        if not value_str:
            return Decimal("0.00")
        try:
            # Eliminar todo excepto dígitos, puntos y comas
            clean = re.sub(r'[^\d.,]', '', value_str)
            if not clean: return Decimal("0.00")
            
            # Caso 1.234,56 (Español/VE) -> Replace . with nothing, , with .
            if ',' in clean and '.' in clean:
                if clean.find('.') < clean.find(','):
                     clean = clean.replace('.', '').replace(',', '.')
                else:
                     clean = clean.replace(',', '')
            
            elif ',' in clean:
                 # Asumimos coma como decimal si es el único separador
                 clean = clean.replace(',', '.')
            
            return Decimal(clean)
        except Exception:
            return Decimal("0.00")

    def parse(self, html_content: str, source_hint: str = "") -> Dict[str, Any]:
        soup = BeautifulSoup(html_content, 'html.parser')
        text_content = soup.get_text().upper()
        # print(f"DEBUG: Content Length: {len(html_content)}")
        # print(f"DEBUG: Text Content Start: {text_content[:200]}")

        # 1. Detección PDF
        result = None
        # 1. Detección PDF
        # 0. EXCLUSIÓN: Standard KIU / GDS
        # Si tiene marcas claras de ser un boleto estándar de KIU (no web receipt), abortamos
        # para que lo procese el parser de KIU estándar en extract_data_from_text
        if "KIUSYS" in text_content or "PASSENGER ITINERARY RECEIPT" in text_content:
             print("DEBUG: WebReceiptParser saltado (Detectado Standard KIU/GDS)")
             return None

        # 1. Detección PDF (Texto)
        # FIX: Case-insensitive check for keywords (Avior headers can be mixed case)
        text_upper = text_content.upper()
        if "AVIOR" in text_upper and ("RESERVA" in text_upper or "LOCALIZADOR" in text_upper or "PNR" in text_upper or "CONFIRMACION" in text_upper):
             logger.info("WebReceiptParser: Branch Avior Text detected")
             result = self._parse_avior_text(text_content)

        elif "RUTACA AIRLINES" in text_content or "TICKETS EMITIDOS CON ÉXIT O" in text_content or "TICKETS RUTACA" in text_content:
             if not soup.find('table'):
                 print("DEBUG: Branch Rutaca Text detected")
                 result = self._parse_rutaca_text(text_content)

        # 2. Detección HTML
        elif 'ESTELAR' in text_content and ('TICKETS ESTELAR' in text_content or 'TICKETS EMITIDOS' in text_content):
            print("DEBUG: Branch Estelar HTML detected")
            result = self._parse_estelar(soup)
        
        # Avior no siempre dice "AVIOR" en texto (es imagen), pero tiene IDs únicos
        # Se agrego soporte para bookingId
        elif soup.find(id="passengerName") and soup.find(id="ticket") and (soup.find(id="pnr") or soup.find(id="bookingId")):
             print("DEBUG: Branch Avior HTML detected")
             result = self._parse_avior(soup)
            
        elif 'RUTACA' in text_content or 'TICKETS RUTACA' in text_content:
            print("DEBUG: Branch Rutaca HTML detected")
            result = self._parse_rutaca(soup)

        # VALIDATION BLOCK
        if result:
            # Check for PENDIENTE in single result or list of tickets
            is_valid = True
            if 'tickets' in result:
                for t in result['tickets']:
                    if t.get('NUMERO_DE_BOLETO') == 'PENDIENTE':
                        is_valid = False
                        break
            else:
                 if result.get('NUMERO_DE_BOLETO') == 'PENDIENTE':
                     is_valid = False
            
            if not is_valid:
                print("DEBUG: WebReceiptParser extracted PENDIENTE ticket. Returning None to trigger Fallback.")
                return None
            return result

        print("DEBUG: No recognizable format found in WebReceiptParser")
        return None # Return None to allow fallback to Generic/AI parsers


    def _identify_airline(self, ticket_number: str) -> str:
        """
        Deduce la aerolínea basada en el prefijo del boleto (IATA 3-digits).
        052 -> ESTELAR
        742 -> AVIOR
        765 -> RUTACA
        """
        clean_tkt = re.sub(r'[^\d]', '', ticket_number)
        if clean_tkt.startswith("052"):
            return "AEROLINEAS ESTELAR LATINOAMERICA C.A."
        elif clean_tkt.startswith("742"):
            return "AVIOR AIRLINES C.A"
        elif clean_tkt.startswith("765"):
            return "RUTACA AIRLINES"
        elif clean_tkt.startswith("765"):
            return "RUTACA AIRLINES"
        return "AEROLINEA DESCONOCIDA"

    def _get_airline_data_from_db(self, airline_name: str, default_agent: str, default_address: str) -> Dict[str, str]:
        """
        Busca la aerolínea en Cliente o Proveedor para obtener dirección y agente.
        Prioridad: Cliente -> Proveedor -> Default Hardcoded.
        User Requirement: "Estelar, Avior, Rutaca estan guardados como clientes"
        """
        try:
            # Importación local para evitar Circular Import al inicio
            from core.models import Cliente, Proveedor
            
            # Buscar en Clientes (Prioridad User)
            # Intentar match exacto o contains
            cliente = Cliente.objects.filter(nombres__icontains=airline_name).first() or \
                      Cliente.objects.filter(apellidos__icontains=airline_name).first()
                      
            if cliente:
                logger.info(f"Datos de Aerolínea encontrados en Cliente: {cliente}")
                return {
                    'agente': default_agent, # EL CLIENTE NO SUELE TENER EL AGENT ID, SE MANTIENE EL DE KIU
                    'direccion': cliente.direccion or default_address
                }

            # Buscar en Proveedores (Fallback lógico)
            proveedor = Proveedor.objects.filter(nombre__icontains=airline_name).first()
            if proveedor:
                logger.info(f"Datos de Aerolínea encontrados en Proveedor: {proveedor}")
                return {
                    'agente': default_agent, 
                    'direccion': proveedor.direccion or default_address
                }
                
        except Exception as e:
            logger.warning(f"No se pudo consultar DB para datos de aerolínea: {e}")
            
        return {'agente': default_agent, 'direccion': default_address}


    def _parse_avior_text(self, text: str) -> Dict[str, Any]:
        """Parsea impresiones web de Avior (PDF/Texto plano). Soporta Multi-Pax."""
        # Regex Helpers
        def get_match(pattern, group=1, default=""):
            m = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            return m.group(group).strip() if m else default

        # 1. Datos Generales
        pnr = get_match(r"(?:Código|Cdigo|Codigo) de reserva:\s*([A-Z0-9]{6})") or \
              get_match(r"(?:Reserva|Localizador|PNR|Booking Ref)[:\.\s]+([A-Z0-9]{6})")
        
        # 2. Pasajeros y Tickets
        # Estrategia: Buscar explícitamente el patrón de 13 dígitos que empiece por 742 (Avior)
        # dado que el layout es columnar (Header... \n Value...)
        # "Número de tiquete: Teléfono:\n7420200050353 N/A"
        
        ticket_matches = re.findall(r"742\d{10}", text)
        if not ticket_matches:
             # Fallback genérico
             ticket_matches = re.findall(r"(?:Número|Nmero) de tiquete:.*(?:\n|\r).*?(\d{13})", text, re.IGNORECASE)

        unique_tickets = sorted(list(set(ticket_matches)))
        num_pax = len(unique_tickets)
        
        if num_pax == 0:
             # Fallback si falla la regex estricta
             pass 

        # 3. Montos Globales
        # "Total \n 1 VES 27.450,15 ... VES 34987.29"
        # Buscamos el último monto en VES de la línea de totales
        # FIX: Added re.DOTALL to handle multiple newlines between Total header and values
        total_group = "0"
        
        # Regex explanation:
        # Total followed by some chars (including newlines due to DOTALL)
        # looking for VES group at the end or near end.
        # We limit the lookahead to avoid grabbing footer text.
        total_match = re.search(r"Total\s*[\n\r]+(?:.{0,200}?)(VES\s*[\d\.,]+)", text, re.IGNORECASE | re.DOTALL)
        if total_match:
             # If multiple matches (e.g. per pax), we usually want the last one in the block or the grand total
             # regex above finds the first group.
             # Let's verify if there are multiple VES amounts.
             candidates = re.findall(r"Total\s*[\n\r]+(?:.{0,200}?)(VES\s*[\d\.,]+)", text, re.IGNORECASE | re.DOTALL)
             if candidates:
                 total_group = candidates[-1] # Take the last one (Grand Total usually)
        else:
             # Intento genérico línea simple
             total_group = get_match(r"Total\s.*?(?:USD|VES)?\s*([\d\s.,]+)", group=1)

        total_clean = re.sub(r'(\d)\s+(\d)', r'\1\2', total_group)
        total_val = self._clean_money(total_clean)
        
        # Impuestos
        tax_group = get_match(r"Tasas \+ impuestos\s*(?:USD|VES)?\s*([\d\s.,]+)", group=1)
        tax_clean = re.sub(r'(\d)\s+(\d)', r'\1\2', tax_group)
        tax_val = self._clean_money(tax_clean)
        
        # Prorrateo
        if num_pax > 0:
            total_por_pax = total_val / num_pax
            tax_por_pax = tax_val / num_pax
        else:
            total_por_pax = total_val
            tax_por_pax = tax_val
            
        base_por_pax = total_por_pax - tax_por_pax

        # 4. Itinerario (Común para todos)
        # "Información del viaje: BARCELONA - CARACAS"
        # FIX: Added DOTALL/Multiline handling because route text can span lines
        # Captures everything until "Trayecto", "Fecha", "Salida" or "Ordenado"
        route_header = get_match(r"Información del viaje:[\s\r\n]*([^\r\n]*(?:[\r\n]+[^\r\n]*)*?)(?:\s+Trayecto|\s+Fecha|\s+Salida|\s+Ordenado)", group=1)
        if not route_header:
            # Fallback simple
             route_header = get_match(r"Información del viaje:\s*(.*)")
        
        origen, destino = "ORI", "DES"
        if "-" in route_header:
            parts = route_header.split("-")
            origen = parts[0].strip().replace("PUERT O", "PUERTO").replace("PUER TO", "PUERTO")
            destino = parts[1].strip()
        else:
            # Check for multi-line (Caracas \n Puerto Ordaz)
            if '\n' in route_header or '\r' in route_header:
                lines = [l.strip() for l in route_header.replace('\r', '\n').split('\n') if l.strip()]
                if len(lines) >= 2:
                    origen = lines[0].replace("PUERT O", "PUERTO").replace("PUER TO", "PUERTO")
                    destino = lines[1]
        
        # Now flatten for cleanup if needed, but we already extracted origen/destino
        route_header = re.sub(r'[\r\n]+', ' ', route_header).strip()
        
        vuelo_num = get_match(r"Vuelo:\s*(\d+)")
        hora_salida = get_match(r"Salida\s*(\d{2}:\d{2})") or "00:00"
        hora_llegada = get_match(r"Llegada\s*(\d{2}:\d{2})") or "00:00"
        
        # Fechas
        # Fechas
        # Buscamos fecha con día de semana para evitar fecha del email (Ej: "Jueves, 29 de Enero de 2026")
        date_pattern = r"(?:Lunes|Martes|Miércoles|Miercoles|Jueves|Viernes|Sábado|Sabado|Domingo)\w*,\s*(\d{1,2})\s*de\s*(\w+)\s*de\s*(\d{4})"
        d_match = re.search(date_pattern, text, re.IGNORECASE)
        
        day = "01"
        month_str = "enero"
        year = str(datetime.now().year)
        fecha_display = "Fecha Desconocida"
        
        if d_match:
            day = d_match.group(1).zfill(2)
            month_str = d_match.group(2).lower()
            year = d_match.group(3)
        
        meses = {
            'enero': '01', 'febrero': '02', 'marzo': '03', 'abril': '04', 'mayo': '05', 'junio': '06',
            'julio': '07', 'agosto': '08', 'septiembre': '09', 'octubre': '10', 'noviembre': '11', 'diciembre': '12'
        }
        meses_abbr = {
            'enero': 'ENE', 'febrero': 'FEB', 'marzo': 'MAR', 'abril': 'ABR', 'mayo': 'MAY', 'junio': 'JUN',
            'julio': 'JUL', 'agosto': 'AGO', 'septiembre': 'SEP', 'octubre': 'OCT', 'noviembre': 'NOV', 'diciembre': 'DIC'
        }
        
        mes_num = meses.get(month_str, '01')
        mes_abbr = meses_abbr.get(month_str, 'XXX').upper()
        year_short = year[-2:] if len(year) == 4 else year
        
        # Formato solicitado: DDMMMYY (29ENE26) - Flight Date
        fecha_display = f"{day}{mes_abbr}{year_short}"
        fecha_iso = f"{year}-{mes_num}-{day}"
        
        # ISSUE DATE (Today in DDMMMYY)
        now = datetime.now()
        spanish_months_list = ['enero','febrero','marzo','abril','mayo','junio','julio','agosto','septiembre','octubre','noviembre','diciembre']
        month_issue_name = spanish_months_list[now.month - 1]
        issue_abbr = meses_abbr.get(month_issue_name, 'XXX')
        issue_year_short = str(now.year)[-2:]
        issue_day = str(now.day).zfill(2)
        fecha_emision_ddmmmyy = f"{issue_day}{issue_abbr}{issue_year_short}"

        # Construir lista de tickets
        tickets = []
        
        # NOMBRES (Layout Columnar)
        # Nombre: Correo:
        # JUAN CARLOS VELEZ NAIDYCOHEN@GMAIL.COM
        
        # DEBUG CRITICO: Ver qué texto estamos recibiendo realmente
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"🔍 DEBUG AVIOR RAW TEXT: {text[:500]}...") # Primeros 500 chars

        # 2. Pasajeros y Tickets
        nombres = []
        # 2. Pasajeros y Tickets
        nombres = []
        # Estrategia 1: Captura de bloque "Nombre: ... Correo:" con soporte de nuevas líneas (Bilingüe)
        # Headers: Nombre, Name, Passenger Name
        # Delimiters: Correo, Email, Documento, Document, Doc, Id, Tiquete, Ticket
        
        # Regex construida para flexibilidad
        header_pattern = r"(?:Nombre|Name|Passenger Name|Passenger)\s*:"
        delimiter_pattern = r"(?:Correo|Email|Documento|Document|Doc|Id|Tiquete|Ticket|Tel|Phone)"
        
        match_block = re.search(f"{header_pattern}\\s*(.*?)\\s*(?:{delimiter_pattern}:)", text, re.IGNORECASE | re.DOTALL)
        if match_block:
             raw_name = match_block.group(1).strip()
             # Aplanar: Reemplazar saltos de línea con espacio
             clean_name = re.sub(r'[\r\n]+', ' ', raw_name).strip()
             # Limpiar basura posible del inicio/fin
             clean_name = clean_name.strip(":-_ ")
             
             # Filtro anti-ruido ("No" detectado por usuario)
             if len(clean_name) > 2 and clean_name.lower() != "no":
                 nombres.append(clean_name)

        if not nombres:
             # Estrategia 2: Búsqueda línea por línea (Legacy mejorado Bilingüe)
             lines = text.splitlines()
             for i, line in enumerate(lines):
                 line_upper = line.upper()
                 if ("NOMBRE:" in line_upper or "NAME:" in line_upper) and \
                    ("CORREO:" in line_upper or "EMAIL:" in line_upper or "DOC:" in line_upper):
                     if i + 1 < len(lines):
                         # Tomar la siguiente línea
                         raw_name_line = lines[i+1].strip()
                         # Si la siguiente línea es muy corta o parece parte del nombre, la unimos
                         if i + 2 < len(lines) and "@" not in raw_name_line and len(raw_name_line) < 20:
                             raw_name_line += " " + lines[i+2].strip()
                         
                         # Limpieza básica
                         parts = raw_name_line.split()
                         name_parts = []
                         for p in parts:
                             # Stop words
                             if "@" in p or "IDEPAZ" in p or "ID:" in p.upper() or "DOC" in p.upper(): break
                             name_parts.append(p)
                         
                         extracted = " ".join(name_parts).strip()
                         
                         # Heuristic: If single name (e.g. "HECTOR"), check next line for surname
                         if len(extracted.split()) == 1 and i + 2 < len(lines):
                            next_line_cand = lines[i+2].strip()
                            # If next line is text (no digits, no colon, reasonably short)
                            if next_line_cand and ":" not in next_line_cand and not any(char.isdigit() for char in next_line_cand):
                                extracted += " " + next_line_cand
                         
                         if len(extracted) > 2:
                             nombres.append(extracted)
                         break
        
        if not nombres:
             # Estrategia 3: Extracción explícita por etiquetas estándar
             patterns_name = [
                 r'(?:NAME|NOMBRE|PASSENGER)\s*[:\s]*(.+)', 
                 r'(?:NAME|NOMBRE)/\s*([A-Z\s]+)',
                 r'(?:NAME|NOMBRE)/(?:NAME|NOMBRE)\s*[:\s]*(.+)',
                 r'(?:NAME|NOMBRE)[/:\s]+(.+)'
             ]
             for p in patterns_name:
                 m = re.search(p, text, re.IGNORECASE)
                 if m:
                     cand = m.group(1).strip()
                     if len(cand) > 2:
                        nombres.append(cand)
                        break
        
        if not nombres:
             # Estrategia 3: Extracción explícita por etiquetas estándar
             patterns_name = [r'NAME/NOMBRE\s*[:\s]*(.+)', r'NAME\s*[:\s]*(.+)', r'NOMBRE\s*[:\s]*(.+)']
             for p in patterns_name:
                 m = re.search(p, text, re.IGNORECASE)
                 if m:
                     nombres.append(m.group(1).strip())
                     break
        
        # Limpieza final
        nombres = [re.sub(r'<[^>]+>', '', n).strip() for n in nombres if n.strip() and "tiquete" not in n.lower()]
        
        # 2. Tickets, Montos e Itinerario
        ticket_matches = re.findall(r"742\d{10}", text)
        if not ticket_matches:
             ticket_matches = re.findall(r"(?:Número|Nmero) de tiquete:.*(?:\n|\r).*?(\d{13})", text, re.IGNORECASE)

        unique_tickets = sorted(list(set(ticket_matches)))
        num_pax = len(unique_tickets)
        
        # Montos
        total_match = re.search(r"Total\s*[\n\r]+(?:.{0,200}?)(VES\s*[\d\.,]+)", text, re.IGNORECASE | re.DOTALL)
        total_group = total_match.group(1) if total_match else get_match(r"Total\s.*?(?:USD|VES)?\s*([\d\s.,]+)", group=1)
        total_val = self._clean_money(re.sub(r'(\d)\s+(\d)', r'\1\2', total_group))
        
        # Bilingual Taxes
        tax_group = get_match(r"(?:Tasas \+ impuestos|Taxes|Taxes \+ Fees|Impuestos)\s*(?:USD|VES)?\s*([\d\s.,]+)", group=1)
        tax_val = self._clean_money(re.sub(r'(\d)\s+(\d)', r'\1\2', tax_group))
        
        total_por_pax = total_val / max(num_pax, 1)
        tax_por_pax = tax_val / max(num_pax, 1)
        base_por_pax = total_por_pax - tax_por_pax

        # --- PARSER DE ITINERARIO (Robustez Extrema) ---
        # Aplanamos el texto para la regex del itinerario (manejo de saltos de línea en destino)
        text_flat = text.replace('\n', ' ').replace('\r', ' ')
        
        vuelos_data = []
        # Regex relajada:
        # Permite origen pegado al código de aerolínea (ej: "DO9V")
        # El código de aerolínea (9V) son 2 caracteres alfanuméricos
        # El número de vuelo (\d{3,4}) viene pegado O separado por espacio
        # FIX: Removed '$' anchor to allow finding flights in middle of text
        itin_regex = re.compile(
            r'([A-Z\s\./-]+?)\s*([A-Z0-9]{2})\s*(\d{3,4})\s+([A-Z])\s+(\d{1,2}[A-Z]{3})\s+(\d{4})\s+(\d{4}).*?([A-Z\s]{3,})',
            re.IGNORECASE
        )
        
        # Buscamos en el texto aplanado
        itin_matches = itin_regex.finditer(text_flat)
        for match in itin_matches:
            v_ori = match.group(1).strip()
            v_code = match.group(2).strip()
            v_num = match.group(3).strip()
            v_clase = match.group(4).strip()
            v_date = match.group(5).strip()
            v_dep = match.group(6).strip()
            v_arr = match.group(7).strip()
            v_dest = match.group(8).strip()
            
            # Limpieza de origen (ej: "BOGOTA-EL DO" -> "BOGOTA")
            
            vuelos_data.append({
                'origen': v_ori,
                'destino': v_dest,
                'numero_vuelo': f"{v_code}{v_num}",
                'fecha': v_date.upper(),
                'hora_salida': f"{v_dep[:2]}:{v_dep[2:]}",
                'hora_llegada': f"{v_arr[:2]}:{v_arr[2:]}",
                'clase': v_clase,
                'aerolinea': 'AVIOR AIRLINES'
            })
            
        # Fallback simple si falla la regex de segmentos
        if not vuelos_data:
             # Bilingual Route Header
             route_header = get_match(r"(?:Información del viaje|Flight Information|Itinerary|Itinerario|Route)[:\s\r\n]*([A-Z -]+)", group=1)
             origen = route_header.split('-')[0].strip() if '-' in route_header else "ORI"
             destino = route_header.split('-')[1].strip() if '-' in route_header else "DES"
             vuelos_data.append({
                'origen': origen,
                'destino': destino,
                'numero_vuelo': f"9V {get_match(r'(?:Vuelo|Flight):\s*(\d+)')}",
                'fecha': 'VER RUTA',
                'hora_salida': get_match(r"Salida\s*(\d{2}:\d{2})") or "00:00",
                'hora_llegada': get_match(r"Llegada\s*(\d{2}:\d{2})") or "00:00",
                'clase': get_match(r"Cabina:\s*(\w+)"),
                'aerolinea': 'AVIOR AIRLINES'
             })

        fecha_emision = get_match(r"Emitido en:\s*(\d{2}\s*\w{3}\s*\d{4})")

        for i in range(max(num_pax, 1)):
            tickets.append({
                'SOURCE_SYSTEM': 'AVIOR_WEB_PDF',
                'NUMERO_DE_BOLETO': unique_tickets[i] if i < len(unique_tickets) else "PENDIENTE",
                'NOMBRE_DEL_PASAJERO': nombres[i].upper() if i < len(nombres) else "PASAJERO DESCONOCIDO",
                'SOLO_NOMBRE_PASAJERO': (nombres[i].split('/')[1] if '/' in nombres[i] else nombres[i].split()[0]) if i < len(nombres) else "",
                'CODIGO_RESERVA': get_match(r"reserva:\s*([A-Z0-9]{6})"),
                'TOTAL_IMPORTE': str(total_por_pax),
                'TOTAL_MONEDA': 'VES', 
                'FECHA_EMISION': fecha_emision,
                'vuelos': vuelos_data
            })

        return {'is_multi_pax': True, 'tickets': tickets}


    def _clean_money(self, val_str: str) -> Decimal:
        """Convierte string de moneda a Decimal. Soporta ES (1.000,00) y US (1,000.00)."""
        if not val_str: return Decimal(0)
        # Quitar Bs, USD, espacios
        clean = re.sub(r'[^\d,.]', '', val_str).strip()
        
        # Heurística:
        # Si tiene ",", asumimos formato ES (o US con miles, pero priorizamos ES para ser consistente con Venezuela)
        # Casos:
        # 20.226,08 -> ES.
        # 1,234.56 -> US.
        # 27472.29 -> US (sin miles).
        
        if ',' in clean and '.' in clean:
            # Ambos presentes. Decidir cual es cual por pos.
            last_dot = clean.rfind('.')
            last_comma = clean.rfind(',')
            if last_dot > last_comma:
                # 1,234.56 (US)
                clean = clean.replace(',', '') # Quitar miles
                # clean is now 1234.56, ready for Decimal
            else:
                # 1.234,56 (ES)
                clean = clean.replace('.', '').replace(',', '.')
        elif ',' in clean:
            # Solo coma: 123,45 (ES decimal) o 1,234 (US miles)
            # Asumimos ES decimal si es al final
            # 1,234 -> 1234.00 ? O 1.234
            # Heurística VE: coma es decimal.
            clean = clean.replace(',', '.')
        elif '.' in clean:
            # Solo punto: 123.45 (US decimal) o 1.234 (ES miles)
            # Si tiene múltiples puntos: 1.234.567 -> ES miles
            if clean.count('.') > 1:
                clean = clean.replace('.', '')
            else:
                # Un solo punto.
                # 27472.29 -> US Decimal.
                # 1.000 -> ES Miles?
                # Si tiene 2 decimales exactos, asumimos decimal.
                parts = clean.split('.')
                if len(parts[1]) == 2: # .99, .00, .29
                    pass # Es formato US standard, dejarlo
                else:
                    # 1.000 -> ES Miles
                    clean = clean.replace('.', '')
        
        try:
            return Decimal(clean)
        except:
            return Decimal(0)

    def _parse_estelar(self, soup: BeautifulSoup) -> Dict[str, Any]:
        logger.info("Detectado formato Web: ESTELAR (Manifiesto)")
        
        # 1. Extracción de Datos Comunes (Vuelo, Ruta, Totales)
        # Intentar buscar el total consolidado
        total_str = "0"
        # Buscamos 'Total' y el valor siguiente
        # Estelar usa tablas anidadas dificiles, buscamos por texto
        total_node = soup.find(string=re.compile("Total", re.I))
        if total_node:
            # A veces el valor está en el siguiente TD o P
            # En el ejemplo: <p>Total</p><p>Bs 106018.7</p>
            parent = total_node.parent
            # Buscar el siguiente tag p con valor
            # Navegación heurística
            val_node = parent.find_next("p") if parent else None
            if val_node:
                total_str = val_node.get_text().strip()
        
        total_monto = self._clean_money(total_str)
        
        # Ruta y Fechas
        # Buscamos "Detalles de Viaje"
        # En ejemplo: San Antonio del Táchira -> Caracas
        origen = "N/A"
        destino = "N/A"
        fecha_emision = "N/A" # No suele venir explícita, usamos la del correo o hoy
        
        # 2. Extracción de Pasajeros (Loop)
        tickets = []
        
        # En el HTML de Estelar, los pasajeros vienen en bloques.
        # Buscamos "Nombre", "Apellido", "Número de ticket"
        # Estrategia: Buscar todos los 'Número de ticket' y subir para encontrar el nombre asociado
        
        # Buscamos todos los nodos que digan "Número de ticket"
        ticket_labels = soup.find_all(string=re.compile("Número de ticket", re.I))
        
        num_pax = len(ticket_labels)
        if num_pax == 0:
            return {'error': 'No se encontraron pasajeros en Estelar Web'}

        # Prorrateo de montos
        monto_por_pax = total_monto / num_pax if num_pax > 0 else 0
        
        for label in ticket_labels:
            # Estructura típica: 
            # TD -> P: "Número de ticket"
            # TD Siguiente -> P: "0520270638379"
            # Lógica corregida: El label y el valor pueden estar en párrafos <p> dentro del MISMO <td>
            # <td ...>
            #    <p>Número de ticket</p>
            #    <p>0520270638379</p>
            # </td>
            
            
            num_boleto = "PENDIENTE"
            label_p = label.parent
            label_td = None # Inicializar
            
            if label_p.name == 'p':
                 label_td = label_p.parent 
                 # Intento 1: Sibling P (mismo TD)
                 value_p = label_p.find_next_sibling("p")
                 if value_p:
                     num_boleto = value_p.get_text(strip=True)
                 else:
                     # Fallback Intento 2: Siguiente TD (estructura de tabla)
                     if label_td and label_td.name == 'td':
                        value_td = label_td.find_next_sibling("td")
                        if value_td:
                             num_boleto = value_td.get_text(strip=True)
            else:
                 # Fallback original
                 label_td = label.parent.parent 
                 value_td = label_td.find_next_sibling("td")
                 if value_td:
                     num_boleto = value_td.get_text(strip=True)
            
            # Estructura: 
            # Table(Pax) -> Table(Name/Surname)
            #            -> Table(Email/Ticket)
            # Label está en Table(Email/Ticket).
            # Subimos 1 nivel para llegar a Table(Pax) que contiene ambos bloques.
            # En el HTML observado:
            # Table(Row) -> TD -> Table(Email/Ticket) ...
            # El "Container" del pasajero parece ser la tabla que envuelve todo el bloque del pax.
            
            # Intentamos navegación relativa hacia atrás.
            # El bloque Nombre está ANTES del bloque Ticket.
            # Buscamos el TR anterior o la Tabla anterior en el mismo nivel.
            
            # Estrategia robusta:
            # Navegar hacia arriba hasta encontrar un nodo que contenga también "Nombre".
            # Pero cuidado con subir demasiado.
            # En el HTML muestra: Table(Pax) contiene Table(Name) y Table(Ticket).
            # ticket_label -> p -> td -> tr -> tbody -> table (TicketTable) -> td -> tr -> tbody -> table (PaxTable)
            
            # Subimos hasta encontrar la tabla que contiene este ticket específico
            pax_table = label_td.find_parent("table").find_parent("table").find_parent("table")
            
            # Verificamos si esta tabla tiene "Nombre". Si no (porque subimos poco o mucho), ajustamos.
            # Si subimos mucho (al wrapper de todos), encontraremos el primer nombre.
            # Debemos asegurarnos que 'pax_table' es UNICAMENTE del pasajero actual.
            # El HTML tiene <hr> entre pasajeros? Si.
            
            # Alternativa: Buscar "Nombre" solo dentro de pax_table.
            # Si pax_table es el wrapper global, fallará (siempre dará el 1ro).
            # Asumamos que find_parent("table") x 3 es correcto para el bloque individual.
            
            # Para estar seguros, buscamos el "Nombre" mas cercano PREVIO al ticket.
            # find_previous("p", string=...)
            
            nombre_label = label_td.find_previous(string=re.compile("Nombre", re.I))
            nombre_val = "DESCONOCIDO"
            if nombre_label:
                # Verificar que este Nombre pertenece a ESTE bloque. 
                # Si el ticket es el 2do, el nombre previo debería ser el 2do. 
                # Si find_previous funciona linealmente, es correcto.
                n_td = nombre_label.parent.parent
                val_p = nombre_label.parent.find_next_sibling("p")
                if val_p: nombre_val = val_p.get_text(strip=True)

            apellido_label = label_td.find_previous(string=re.compile("Apellido", re.I))
            apellido_val = ""
            if apellido_label:
                a_p = apellido_label.parent
                val_a_p = a_p.find_next_sibling("p")
                if val_a_p: apellido_val = val_a_p.get_text(strip=True)
                
            nombre_completo = f"{apellido_val}/{nombre_val}".upper()
            
            # PNR
            pnr = "NO_PNR"
            pnr_label = soup.find(string=re.compile("Código de reserva", re.I))
            if pnr_label:
                # Buscar en el siguiente TD o P cercano
                # En ejemplo: <p>Código de reserva:</p> ... <a>...<span>WGNBLG</span></a>
                # A veces está lejos. Usamos búsqueda global si falla local.
                pnr_container = pnr_label.find_parent("table")
                if pnr_container:
                    pnr = pnr_container.get_text().replace("Código de reserva:", "").strip()[:6]

            # Construir objeto ticket
            ticket_data = {
                'SOURCE_SYSTEM': 'ESTELAR_WEB', # Usaremos plantilla especial
                'NUMERO_DE_BOLETO': num_boleto,
                'NOMBRE_DEL_PASAJERO': nombre_completo,
                'SOLO_NOMBRE_PASAJERO': nombre_val.upper(),
                'CODIGO_RESERVA': pnr,
                'SOLO_CODIGO_RESERVA': pnr,
                'CODIGO_IDENTIFICACION': 'PENDIENTE',
                'FECHA_EMISION': datetime.now().strftime("%d-%m-%Y"),
                'TOTAL_IMPORTE': str(monto_por_pax),
                'TOTAL_MONEDA': 'VES', # Estelar Web suele ser Bs
                'TARIFA_IMPORTE': str(monto_por_pax * Decimal('0.7')), # Estimado
                'IMPUESTOS': str(monto_por_pax * Decimal('0.3')), # Estimado
                'NOMBRE_AEROLINEA': 'AEROLINEAS ESTELAR LATINOAMERICA C.A.',
                'AGENTE_EMISOR': 'CCS00ESKA',
                'DIRECCION_AEROLINEA': 'TORRE ESTELAR CALLE LONDRES EDIF LAS MERCEDES, MUNICIPIO BARUTA, EDO MIRANDA, VENEZUELA',
                'vuelos': [] # Se llenará con info genérica o extraída
            }
            # Intento de extracción de vuelos detallados
            vuelos = self._extract_flights_common(soup, airline_name='ESTELAR')
            
            # Asignar a la estructura del ticket
            ticket_data['vuelos'] = vuelos
            if vuelos:
                # Usar el primer vuelo para ruta si no hay nada mejor
                origen = vuelos[0].get('origen','N/A')
                destino = vuelos[-1].get('destino','N/A')
            
            # User Requirement: "OFFICE ID de KIU que seria el Agente Emisor... guardados como clientes"
            db_data = self._get_airline_data_from_db('ESTELAR', 'CCS00ESKA', 'TORRE ESTELAR CALLE LONDRES EDIF LAS MERCEDES, MUNICIPIO BARUTA, EDO MIRANDA, VENEZUELA')

            tickets.append(ticket_data)
            
            # Update data inside dict before append was tricky, let's update reference
            ticket_data['AGENTE_EMISOR'] = db_data['agente']
            ticket_data['DIRECCION_AEROLINEA'] = db_data['direccion']
            
        return {
            'is_multi_pax': True,
            'tickets': tickets
        }

    def _parse_avior(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """
        Parsea boletos de Avior usando los IDs específicos del HTML.
        Soporta Multi-Pax (Múltiples passengerName/ticket).
        """
        logger.info("Detectado formato Web: AVIOR (HTML Multi-Pax)")
        
        # Helper extraction
        def get_text_by_id(node, eid):
            found = node.find(id=eid) if node else soup.find(id=eid)
            return found.get_text(strip=True) if found else ""

        # 1. Detectar Pasajeros y Tickets
        # Buscar TODOS los nodos con id="passengerName" y "ticket"
        pax_nodes = soup.find_all(id="passengerName")
        ticket_nodes = soup.find_all(id="ticket")
        
        # Fallback si find_all falla o retorna vacio (raro si es avior html)
        if not pax_nodes:
            single_pax = soup.find(id="passengerName")
            if single_pax: pax_nodes = [single_pax]
            else: return {'error': 'No se encontraron pasajeros (passengerName)'}

        num_pax = len(pax_nodes)
        
        # 2. Extracciones Globales (PNR, Totales)
        pnr_node = soup.find(id="pnr") or soup.find(id="bookingId")
        pnr = pnr_node.get_text(strip=True) if pnr_node else "NO_PNR"
        
        # Totales
        total_node = soup.find(id="amountAfterTax") or soup.find(id="totalAmount")
        total_str = total_node.get_text(strip=True) if total_node else "0"
        
        # Moneda Forzada a VES para Avior Web
        moneda = "VES"
        
        total_val = self._clean_money(total_str)
        
        # Impuestos
        tax_node = soup.find(id="taxes")
        tax_val = self._clean_money(tax_node.get_text(strip=True)) if tax_node else Decimal(0)
        base_val = self._clean_money(soup.find(id="amountBeforeTax").get_text(strip=True)) if soup.find(id="amountBeforeTax") else (total_val - tax_val)
        
        # Prorrateo
        if num_pax > 0:
            total_por_pax = total_val / num_pax
            tax_por_pax = tax_val / num_pax
            base_por_pax = base_val / num_pax
        else:
             total_por_pax = total_val
             tax_por_pax = tax_val
             base_por_pax = base_val

        # 3. Vuelos (Globales)
        # Extraemos los vuelos una sola vez y los asignamos a todos.
        # Si hubiera duplicados (múltiples tablas), tratamos de deducirlos.
        segments = soup.find_all(id="segment")
        if not segments and soup.find(id="departureName"):
            segments = [soup]
            
        vuelos_procesados = []
        for seg in segments:
            # Helper local para scope de segmento
            def seg_val(eid):
                node = seg.find(id=eid) if seg != soup else soup.find(id=eid)
                return node.get_text(strip=True) if node else ""

            origen = seg_val("departureName")
            destino = seg_val("arrivalName")
            fecha_str = seg_val("date")
            num_vuelo = seg_val("flightNumber") or "-"
            
            # Limpieza Origen/Destino si vienen pegados en hora
            dept_text = seg_val("departure") # "08:40 CARACAS..."
            arr_text = seg_val("arrival")
            
            hora_salida = dept_text.split(' ')[0] if dept_text else "00:00"
            hora_llegada = arr_text.split(' ')[0] if arr_text else "00:00"
            
            if len(dept_text.split(' ')) > 1 and not origen:
                  origen = ' '.join(dept_text.split(' ')[1:]).replace(',', '').strip()
            if len(arr_text.split(' ')) > 1 and not destino:
                  destino = ' '.join(arr_text.split(' ')[1:]).replace(',', '').strip()

            # Parseo Fecha
            fecha_iso = datetime.now().strftime("%Y-%m-%d")
            fecha_display = fecha_str
            if fecha_str:
                try:
                    parts = fecha_str.split(',') 
                    if len(parts) > 1:
                        fecha_display = parts[1].strip()
                        d_parts = fecha_display.lower().split(' de ')
                        if len(d_parts) >= 2:
                             d_day = d_parts[0]
                             d_month = d_parts[1]
                             meses = {
                                'enero': '01', 'febrero': '02', 'marzo': '03', 'abril': '04', 'mayo': '05', 'junio': '06',
                                'julio': '07', 'agosto': '08', 'septiembre': '09', 'octubre': '10', 'noviembre': '11', 'diciembre': '12'
                             }
                             mes_num = meses.get(d_month, '01')
                             year = datetime.now().year
                             if len(d_parts) > 2: year = d_parts[2]
                             fecha_iso = f"{year}-{mes_num}-{d_day.zfill(2)}"
                             fecha_display = f"{d_day} de {d_month}"
                except: pass

            v = {
                'origen': origen,
                'destino': destino,
                'numero_vuelo': f"9V {num_vuelo}" if "9V" not in num_vuelo else num_vuelo,
                'fecha': fecha_display,
                'fecha_salida': fecha_iso,
                'hora_salida': hora_salida,
                'hora_llegada': hora_llegada,
                'clase': seg_val("cabinName") or seg_val("familyName") or "ECONOMIC",
                'equipaje': '1PC',
                'aerolinea': 'AVIOR AIRLINES'
            }
            # Evitar duplicados exactos (si la tabla de vuelos se repite por pasajero)
            if v not in vuelos_procesados:
                vuelos_procesados.append(v)
        
        # 4. Construir lista de Tickets
        tickets = []
        for i, pax_node in enumerate(pax_nodes):
            nombre_pasajero = pax_node.get_text(strip=True).upper()
            
            numero_boleto = "PENDIENTE"
            if i < len(ticket_nodes):
                numero_boleto = ticket_nodes[i].get_text(strip=True)
            
            primer_nombre = nombre_pasajero.split()[0] if nombre_pasajero else ""
            
            # Auto-Detect Airline
            airline_name = self._identify_airline(numero_boleto)

            
            # User Requirement: "OFFICE ID de KIU que seria el Agente Emisor... guardados como clientes"
            db_data = self._get_airline_data_from_db('AVIOR', 'BLA009VWW', 'AV JORGE RODRIGUEZ CC MT NIVEL PB LC 35 ANZOATEGUI')

            tickets.append({
                'SOURCE_SYSTEM': 'AVIOR_WEB',
                'NUMERO_DE_BOLETO': numero_boleto,
                'NOMBRE_DEL_PASAJERO': nombre_pasajero,
                'SOLO_NOMBRE_PASAJERO': primer_nombre,
                'CODIGO_RESERVA': pnr,
                'SOLO_CODIGO_RESERVA': pnr,
                'CODIGO_IDENTIFICACION': 'PENDIENTE',
                'FECHA_EMISION': datetime.now().strftime("%d-%m-%Y"),
                'TOTAL_IMPORTE': str(total_por_pax),
                'TOTAL_MONEDA': moneda,
                'TARIFA_IMPORTE': str(base_por_pax),
                'IMPUESTOS': str(tax_por_pax),
                'NOMBRE_AEROLINEA': airline_name,
                'AGENTE_EMISOR': db_data['agente'],
                'DIRECCION_AEROLINEA': db_data['direccion'],
                'vuelos': vuelos_procesados
            })

        return {
            'is_multi_pax': True, 
            'tickets': tickets
        }


    def _parse_rutaca(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """
        Parsea boletos de Rutaca (Estilo React Email / Tablas).
        """
        logger.info("Detectado formato Web: RUTACA")
        print("DEBUG: _parse_rutaca STARTED")
        
        # 1. Datos del Pasajero
        # Helper seguro
        def get_val_next_p(label_pattern):
            node = soup.find(string=re.compile(label_pattern, re.I))
            if node:
                parent = node.parent
                # Opción 1: P Sibling
                sib = parent.find_next_sibling("p")
                if sib: return sib.get_text(strip=True)
                # Opción 2: TD Sibling (en tabla)
                parent_td = parent.find_parent("td")
                if parent_td:
                    next_td = parent_td.find_next_sibling("td")
                    if next_td: return next_td.get_text(strip=True)
            return ""

        nombre_val = get_val_next_p("Nombre")
        if not nombre_val: # Fallback specific for Rutaca "Nombre" sometimes in 1st col
             pass
             
        apellido_val = get_val_next_p("Apellido")
        
        # Nombre Completo
        nombre_completo = f"{apellido_val}/{nombre_val}".upper()
        
        # Saludo "Hola, RAFAEL" -> Tomar primer nombre
        primer_nombre = ""
        if nombre_val:
             primer_nombre = nombre_val.strip().split()[0].upper()
        
        # 2. Boleto y PNR
        num_boleto = get_val_next_p("Número de ticket") or "PENDIENTE"

        
        pnr_label = soup.find(string=re.compile("Código de reserva", re.I))
        # Estructura: <td..><p>Código...</p></td> <td><p>BFEYHY</p></td> (A veces)
        # Ojo: find_next_sibling("td") desde el td padre
        pnr = "NO_PNR"
        if pnr_label:
             # Subir al TD
             td_label = pnr_label.find_parent("td")
             if td_label:
                 td_val = td_label.find_next_sibling("td")
                 if td_val:
                     pnr = td_val.get_text(strip=True)
        
        # 3. Totales (Bs)
        # Total en tabla final: <p>Total </p><p>Bs 37604.95 </p>
        # Relaxed regex to handle spaces and potential variations
        total_label = soup.find(string=re.compile("Total", re.I))
        total_str = "0"
        
        if total_label:
             # Buscar en el siguiente P del mismo container o celda adyacente
             # Rutaca suele poner label y valor en Ps hermanos o celdas adyacentes
             parent_p = total_label.find_parent("p")
             if parent_p:
                 next_p = parent_p.find_next_sibling("p")
                 if next_p:
                     total_str = next_p.get_text(strip=True)
                 else:
                     # Intentar celda siguiente (Caso tabla)
                     parent_td = parent_p.find_parent("td")
                     if parent_td:
                         next_td = parent_td.find_next_sibling("td")
                         if next_td:
                             total_str = next_td.get_text(strip=True)
                             
        monto = self._clean_money(total_str)
        
        # Impuestos (Estimados o extraídos si posible)
        # "Tasa + Impuestos " (Sample says "Tasa + Impuestos ")
        tax_val = Decimal(0)
        base_val = monto # Default
        
        # Buscar "Tasa + Impuestos" o "Impuestos"
        taxes_label = soup.find(string=re.compile("Impuestos", re.I))
        if taxes_label:
             parent_tax = taxes_label.find_parent("p")
             if parent_tax:
                 next_tax = parent_tax.find_next_sibling("p")
                 if next_tax:
                      tax_val = self._clean_money(next_tax.get_text(strip=True))
                      base_val = monto - tax_val

        ticket_data = {
            'SOURCE_SYSTEM': 'RUTACA_WEB',
            'NUMERO_DE_BOLETO': num_boleto,
            'NOMBRE_DEL_PASAJERO': nombre_completo,
            'SOLO_NOMBRE_PASAJERO': primer_nombre,
            'CODIGO_RESERVA': pnr,
            'SOLO_CODIGO_RESERVA': pnr,
            'CODIGO_IDENTIFICACION': 'PENDIENTE',
            'FECHA_EMISION': datetime.now().strftime("%d-%m-%Y"),
            'TOTAL_IMPORTE': str(monto),
            'TOTAL_MONEDA': 'VES', # Rutaca es en Bolivares
            'TARIFA_IMPORTE': str(base_val),
            'IMPUESTOS': str(tax_val),
            'NOMBRE_AEROLINEA': 'RUTACA AIRLINES',
            'AGENTE_EMISOR': 'BLA005RML',
            'DIRECCION_AEROLINEA': 'AV JESUS SOTO SECTOR AEROPUERTO EDIF TALLER MARES, CIUDAD BOLIVAR, VE',
            'vuelos': self._extract_flights_common(soup, airline_name='RUTACA')
        }
        
        # User Requirement: "OFFICE ID de KIU que seria el Agente Emisor... guardados como clientes"
        db_data = self._get_airline_data_from_db('RUTACA', 'BLA005RML', 'AV JESUS SOTO SECTOR AEROPUERTO EDIF TALLER MARES, CIUDAD BOLIVAR, VE')
        ticket_data['AGENTE_EMISOR'] = db_data['agente']
        ticket_data['DIRECCION_AEROLINEA'] = db_data['direccion']
        
        return {
            'is_multi_pax': True,
            'tickets': [ticket_data]
        }

    def _extract_flights_common(self, soup: BeautifulSoup, airline_name: str = None) -> List[Dict[str, Any]]:
        """
        Extrae segmentos de vuelo buscando la sección 'Detalles de Viaje'.
        Funciona para Estelar y Rutaca que comparten estructura similar (Tablas de React Email).
        """
        vuelos = []
        details_header = soup.find(string=re.compile("Detalles de [Vv]iaje"))
        if not details_header:
            return []

        # Encontrar el container principal de detalles
        # Usualmente es una tabla que contiene el header y luego otras tablas
        # Estructura: Table(Header) -> TD -> TR -> TBODY -> TABLE (Main Wrapper)
        # Buscar tablas que son siblings de la tabla de header
        header_table = details_header.find_parent("table")
        if not header_table: return []
        
        container = header_table.find_parent("td")
        if not container:
            # Fallback si la estructura varía
            container = header_table.parent
            
        if not container: return []
        
        # Buscar todas las tablas que contengan "Hora de salida"
        # Esto nos asegura que es una tabla de vuelo
        # Buscamos en todo el soup para mayor robustez, o limitado al container
        route_tables_markers = soup.find_all(string=re.compile("Hora de salida", re.I))
        
        valid_tables = []
        for rt in route_tables_markers:
            # Subir hasta encontrar el TR que tiene las 2 columnas (Origen | Destino)
            # <p>Hora...</p> -> td -> tr
            # Asegurarse de no duplicar
            table_row = rt.find_parent("tr")
            if table_row and table_row not in valid_tables:
                valid_tables.append(table_row)

        from datetime import datetime
        import locale
        
        # Mapeo manual de meses para evitar dependencias de locale
        meses = {
            'enero': '01', 'febrero': '02', 'marzo': '03', 'abril': '04', 'mayo': '05', 'junio': '06',
            'julio': '07', 'agosto': '08', 'septiembre': '09', 'octubre': '10', 'noviembre': '11', 'diciembre': '12'
        }

        for row in valid_tables:
            cols = row.find_all("td", recursive=False)
            if len(cols) < 2: continue
            
            col_org = cols[0]
            col_dst = cols[1]
            
            # --- Extracción Origen ---
            org_texts = list(col_org.stripped_strings)
            origen = org_texts[0] if org_texts else "N/A"
            """
            Ejemplo strings:
            ['San Antonio del Táchira', 'Hora de salida: 05:30 pm', 'miércoles, 07 de enero', 'Aeropuerto...']
            """
            
            hora_salida = "00:00"
            fecha_salida_iso = "PENDIENTE"
            fecha_display = "PENDIENTE"
            
            for s in org_texts:
                if "Hora de salida" in s:
                    hora_salida = s.replace("Hora de salida:", "").strip()
                elif any(m in s.lower() for m in meses.keys()) and "," in s:
                    # "miércoles, 07 de enero"
                    parts = s.split(',')
                    if len(parts) > 1:
                        date_part = parts[1].strip() # "07 de enero"
                        fecha_display = date_part # Display limpio
                        # Parsear dia y mes
                        try:
                            d_str, m_str = date_part.lower().split(' de ')
                            mes_num = meses.get(m_str.strip(), '01')
                            # Asumir año actual o siguiente
                            now = datetime.now()
                            year = now.year
                            # Heurística simple: año actual
                            fecha_salida_iso = f"{year}-{mes_num}-{d_str.zfill(2)}"
                        except ValueError:
                            pass

            # --- Extracción Destino ---
            dst_texts = list(col_dst.stripped_strings)
            destino = dst_texts[0] if dst_texts else "N/A"
            hora_llegada = "00:00"
            for s in dst_texts:
                if "Hora de llegada" in s:
                    hora_llegada = s.replace("Hora de llegada:", "").strip()

            # --- Extracción Numero Vuelo y Clase ---
            # Usualmente en una tabla separada justo DEBAJO de la row de ruta
            # Navegar al siguiente TABLE o TR
            parent_table = row.find_parent("table") # Tabla de ruta
            # Buscar la tabla gris de info de vuelo que suele seguir
            flight_info_table = parent_table.find_next_sibling("table")
            
            numero_vuelo = "N/A"
            clase = "Y"
            
            if flight_info_table:
                # Buscar "Nro de vuelo"
                nv_label = flight_info_table.find(string=re.compile("Nro de vuelo", re.I))
                if nv_label:
                    # El valor suele ser el siguiente P
                    # <p>Nro..</p> <p>8302</p>
                    nv_p = nv_label.find_parent("p")
                    val_p = nv_p.find_next_sibling("p") if nv_p else None
                    if val_p: numero_vuelo = val_p.get_text(strip=True)
                
                # Clase
                cl_label = flight_info_table.find(string=re.compile("Clase", re.I))
                if cl_label:
                    cl_p = cl_label.find_parent("p")
                    val_cl = cl_p.find_next_sibling("p") if cl_p else None
                    if val_cl: clase = val_cl.get_text(strip=True)
            
            # Construir segmento
            vuelo = {
                'origen': origen,
                'destino': destino,
                'numero_vuelo': numero_vuelo,
                'fecha': fecha_display, # Para display
                'fecha_salida': fecha_salida_iso, # Para logica
                'hora_salida': hora_salida,
                'hora_llegada': hora_llegada,
                'clase': clase,
                'equipaje': '1PC', # Default nacional
                'aerolinea': airline_name or ('ESTELAR' if 'ESTELAR' in str(soup) else 'RUTACA')
            }
            vuelos.append(vuelo)
            
        return vuelos

    def _parse_rutaca_text(self, text: str) -> Dict[str, Any]:
        """
        Parser Regex para PDFs de Rutaca (Outlook Web Print).
        Maneja texto sucio con espacios extra: "C ó d i g o d e r e s e r v a"
        """
        logger.info("Detectado formato Texto/PDF: RUTACA")

        # 1. PNR: "Código de r eserva: BFEYHY" (6 chars)
        pnr_match = re.search(r"ago\s*de\s*r\s*e\s*s\s*e\s*r\s*v\s*a\s*:?\s*([A-Z0-9]{6})", text, re.I)
        if not pnr_match:
             # Try simpler pattern looking for 6 chars after "reserva"
             pnr_match = re.search(r"reserva\s*[:\.]?\s*([A-Z0-9]{6})", text.replace(" ", ""), re.I)
        
        pnr = pnr_match.group(1) if pnr_match else "NO_PNR"
        
        # 2. Ticket: "Númer o de tick et\n7650211236030"
        # Multi-Pax: Buscar todos
        ticket_matches = re.findall(r"tick\s*et\s*(\d{13})", text, re.DOTALL | re.I)
        unique_tickets = sorted(list(set(ticket_matches)))
        num_pax = len(unique_tickets)
        
        # 3. Datos Pasajero (Busqueda general, Rutaca suele poner nombres apilados o separados)
        # "Nombr e\nRAF AELApellido"
        nombres = []
        try:
             # Buscar bloques "Nombre ... Apellido"
             # Regex iterativo
             found_names = re.findall(r"Nombr\s*e\s+(.*?)\s*Apellido\s+(.*?)\s*Corr\s*eo", text, re.DOTALL | re.I)
             for n, a in found_names:
                  n = re.sub(r'\s+', '', n).replace("\n", "").upper()
                  a = re.sub(r'\s+', '', a).replace("\n", "").upper()
                  nombres.append(f"{a}/{n}")
        except:
             pass
        
        if not nombres: nombres = ["PASAJERO/RUTACA"]

        # 4. Totales
        # "Total\nBs 37604.95"
        total_match = re.search(r"Total\s*(?:Bs)?\s*([\d\.,]+)", text, re.I)
        monto = self._clean_money(total_match.group(1)) if total_match else Decimal(0)
        
        # Impuestos: "Tasa + Impuestos\nBs 11186.82"
        tax_match = re.search(r"Tasa\s*\+?\s*Impuestos\s*(?:Bs)?\s*([\d\.,]+)", text, re.I)
        tax_val = self._clean_money(tax_match.group(1)) if tax_match else Decimal(0)
        
        # Prorrateo
        if num_pax > 0:
             monto_por_pax = monto / num_pax
             tax_por_pax = tax_val / num_pax
        else:
             monto_por_pax = monto
             tax_por_pax = tax_val
        
        base_por_pax = monto_por_pax - tax_por_pax

        # 5. Vuelo
        # "San Antonio del T áchir a\nHora de salida: 05:00 pm"
        flight_num = "N/A"
        fn_match = re.search(r"Nro\s*de\s*vuelo\s*(\d+)", text, re.I)
        if fn_match:
             flight_num = fn_match.group(1)
             
        # Origen / Salida
        origen = "RUTACA_ORG"
        hora_salida = "00:00"
        
        salida_match = re.search(r"(.*?)\n.*?Hora\s*de\s*salida.*(\d{2}:\d{2}\s*[ap]m)", text, re.I)
        if salida_match:
            raw_org = salida_match.group(1).strip()
            origen = re.sub(r'([a-zA-Z])\s+([a-zA-Z])', r'\1\2', raw_org).upper()
            hora_salida = salida_match.group(2).replace(" ", "").upper() # 05:00PM

        # Destino / Llegada
        destino = "RUTACA_DES"
        hora_llegada = "00:00"
        llegada_match = re.search(r"(.*?)\n.*?Hora\s*de\s*llegada.*(\d{2}:\d{2}\s*[ap]m)", text, re.I)
        if llegada_match:
            raw_des = llegada_match.group(1).strip()
            destino = re.sub(r'([a-zA-Z])\s+([a-zA-Z])', r'\1\2', raw_des).upper()
            hora_llegada = llegada_match.group(2).replace(" ", "").upper()

        # Fecha: "Viernes, 05 De Diciembr e"
        fecha_display = mt.datetime.now().strftime("%d-%m-%Y")
        fecha_iso = mt.datetime.now().strftime("%Y-%m-%d")
        
        block_vuelo = text
        if "Hora de salida" in text:
             block_vuelo = text.split("Hora de salida")[1]
             
        date_match = re.search(r"(\d{1,2})\s*De\s*([A-Z][a-z\s]+)", block_vuelo, re.I) 
        if date_match:
             day = date_match.group(1)
             raw_month = date_match.group(2).lower().replace(" ", "").replace("\n", "").strip() 
             meses = {
                'enero': '01', 'febrero': '02', 'marzo': '03', 'abril': '04', 'mayo': '05', 'junio': '06',
                'julio': '07', 'agosto': '08', 'septiembre': '09', 'octubre': '10', 'noviembre': '11', 'diciembre': '12'
             }
             for k,v in meses.items():
                  if k in raw_month:
                       year = mt.datetime.now().year 
                       fecha_iso = f"{year}-{v}-{day.zfill(2)}"
                       fecha_display = f"{day}-{v}-{year}"
                       break

        tickets = []
        effective_pax = max(num_pax, 1)
        
        for i in range(effective_pax):
            t_num = unique_tickets[i] if i < len(unique_tickets) else "PENDIENTE"
            full_name = nombres[i] if i < len(nombres) else "PASAJERO DESCONOCIDO"
            primer_nombre = full_name.split("/")[1] if "/" in full_name else full_name.split()[0]
            
            airline_name = self._identify_airline(t_num)

            vuelos = [{
                'origen': origen, 
                'destino': destino, 
                'numero_vuelo': flight_num,
                'fecha': fecha_display,
                'fecha_salida': fecha_iso,
                'hora_salida': hora_salida,
                'hora_llegada': hora_llegada,
                'clase': 'Y',
                'aerolinea': airline_name,
                'equipaje': '1PC'
            }]

            tickets.append({
                'SOURCE_SYSTEM': 'RUTACA_WEB',
                'NUMERO_DE_BOLETO': t_num,
                'NOMBRE_DEL_PASAJERO': full_name,
                'SOLO_NOMBRE_PASAJERO': primer_nombre,
                'CODIGO_RESERVA': pnr,
                'SOLO_CODIGO_RESERVA': pnr,
                'CODIGO_IDENTIFICACION': 'PENDIENTE',
                'FECHA_EMISION': mt.datetime.now().strftime("%d-%m-%Y"),
                'TOTAL_IMPORTE': str(monto_por_pax),
                'TOTAL_MONEDA': 'VES',
                'TARIFA_IMPORTE': str(base_por_pax),
                'IMPUESTOS': str(tax_por_pax),
                'NOMBRE_AEROLINEA': airline_name,
                'AGENTE_EMISOR': 'BLA005RML', 
                'DIRECCION_AEROLINEA': 'AV JESUS SOTO SECTOR AEROPUERTO EDIF TALLER MARES, CIUDAD BOLIVAR, VE',
                'vuelos': vuelos
            })

        return {
            'is_multi_pax': True, 
            'tickets': tickets
        }


        


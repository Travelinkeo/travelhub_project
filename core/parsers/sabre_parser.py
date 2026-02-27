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
        return 'ETICKET RECEIPT' in text_upper and 'RESERVATION CODE' in text_upper
    
    def parse(self, text: str, html_text: str = "") -> ParsedTicketData:
        """Parsea boleto SABRE"""
        
        # Extraer datos básicos
        passenger_name = self.extract_passenger_name_robust(text)
        
        # Fallback si falla la robusta (Sabre specific patterns)
        if passenger_name == 'No encontrado':
             passenger_name = self.extract_field(text, [
                r'(?:Prepared For|Preparado para)\s*\n\s*([A-ZÁÉÍÓÚ0-9\-\/\[\s,\.]+?)(?:\s*\[|\n|$)'
             ])
        
        # Generar nombre de pila para el saludo ("Hola, JUAN")
        solo_nombre_pasajero = "Cliente"
        if passenger_name and passenger_name != "No encontrado":
            # Formato GDS: APELLIDO/NOMBRE
            if '/' in passenger_name:
                parts = passenger_name.split('/')
                if len(parts) > 1:
                    # parts[1] es "NOMBRE SEGUNDO"
                    solo_nombre_pasajero = parts[1].strip().split()[0]
            else:
                # Formato Web: NOMBRE APELLIDO
                solo_nombre_pasajero = passenger_name.strip().split()[0]
        
        document_id = self.extract_field(text, [
            r'(?:Prepared For|Preparado para)\s*[A-ZÁÉÍÓÚ/\s]+\s*\[([A-Z0-9]+)\]',
            r'(?:NÚMERO DE CLIENTE|Customer Number)\s*[:\t\s]*([A-Z0-9-]+)',
        ])
        
        pnr = self.extract_field(text, [
            r'(?:Reservation Code|C[OÓ]DIGO DE RESERVA(?:CI[OÓ]N)?)\s*[:\t\s]*([A-Z0-9]+)'
        ])
        
        # Extraer localizador de aerolínea
        airline_locator = self.extract_field(text, [
            r'(?:Airline Record Locator|C[oó]digo de reservaci[oó]n de\s*la\s*aerol[íi]nea)\s*[:\t\s]*([A-Z0-9]+)',
            r'(?:Record Locator)\s*[:\t\s]*([A-Z0-9]+)'
        ])
        
        issue_date = self.extract_field(text, [
            r'(?:Issue Date|Fecha de Emisi[óo]n|FECHA DE EMISI[ÓO]N)\s*[:\t\s]*([^\n]+)',
            r'emisi[^\n]*?([0-9]{1,2}[A-Z]{3}[0-9]{2,4})', # Captura "emisión: 23APR2025"
            r'\bEMITIDO\s+EL\b\s*[:\s]*([A-Z0-9 ]+)'
        ])
        
        ticket_number = self.extract_field(text, [
            r'(?:Ticket Number|N[ÚU]MERO DE BOLETO|BOLETO)\s*[:\t\s]*([0-9]+)'
        ])
        
        airline = self.extract_field(text, [
            r'(?:Issuing Airline|AEROLÍNEA EMISORA|Aerol[íi]nea Emisora)\s*[:\t\s]*([^\n]+)'
        ])
        # Limpieza de ruido en nombre de aerolínea (ciudades/países pegados)
        airline = re.sub(r'[,/].*$', '', airline).strip()
        
        agent = self.extract_field(text, [
            r'(?:Issuing Agent|AGENTE EMISOR|Agente Emisor)\s*[:\t\s]*([^\n]+)'
        ])
        
        iata = self.extract_field(text, [
            r'(?:IATA Number|IATA|N[úu]mero IATA|NÚMERO IATA)\s*[:\t\s]*([0-9]+)'
        ])
        
        # Extraer vuelos
        flights = self._parse_flights(text, airline_locator)
        
        # LOGIC: Propagar aerolínea del encabezado si los segmentos fallaron
        # Esto soluciona casos (LAN, Copa) donde el segmento no tiene "Operado por" claro
        # pero el encabezado dice "LAN AIRLINES S.A." o "COMPANIA PANAMENA".
        airline_normalized_header = self.normalize_airline_name(airline, ticket_number=ticket_number)
        
        if airline_normalized_header and airline_normalized_header != 'Aerolínea no identificada':
            for f in flights:
                if not f.get('aerolinea') or f.get('aerolinea') == 'Aerolínea no identificada' or f.get('aerolinea') == 'Aerolínea Desconocida':
                    f['aerolinea'] = airline_normalized_header
        
        # Extraer tarifas (MEJORADO - soporta formatos español e inglés)
        # Prioridad para "Tarifa" BASE (no total)
        fare_raw = self.extract_field(text, [
            r'(?<!Base de )\bTarifa\s+(?!total|Total|TOTAL)([A-Z]{3}\s*[0-9,.]+)',    # Español: "Tarifa USD 582,00" (excluyendo "Tarifa total")
            r'(?<!Base de )\bTarifa\s+USD\s+([0-9,.]+)',                              # Variante explicita USD
            r'\bFare\s+(?!Total|total)([A-Z]{3}\s*[0-9,.]+)',                          # Inglés base
            r'\bFARE\s+(?!TOTAL)([A-Z]{3}\s*[0-9,.]+)'
        ])
        
        # Si no encontró tarifa base, podría intentar buscar equiv o similar, pero por ahora dejamos así.
        
        total_raw = self.extract_field(text, [
            r'(?<!Base de )\bTarifa\s+total\s+([A-Z]{3}\s*[0-9,.]+)',                  # Español: "Tarifa total USD 726,30"
            r'\bTotal\s+([A-Z]{3}\s*[0-9,.]+)',
            r'\bTOTAL\s*[:\s]*([A-Z]{3}\s*[0-9,.]+)',
            r'\bTARIFA\s+TOTAL\s*[:\s]*([A-Z]{3}\s*[0-9,.]+)'
        ])
        
        fare_currency, fare_amount = self.extract_currency_amount(fare_raw)
        total_currency, total_amount = self.extract_currency_amount(total_raw)
        
        # Calcular impuestos si tenemos tarifa base y total
        taxes = []
        tax_amount = "0.00"
        if fare_amount and total_amount:
            try:
                # Normalizar montos (quitar comas de miles si existen, o manejar coma decimal)
                # La función self.extract_currency_amount ya devuelve string limpio tipo "123.45" si usó self._clean_money
                # Pero validemos conversión a string por seguridad
                f_str = str(fare_amount)
                t_str = str(total_amount)
                
                f_val = float(f_str.replace(',', '.')) if ',' in f_str and '.' not in f_str else float(f_str)
                t_val = float(t_str.replace(',', '.')) if ',' in t_str and '.' not in t_str else float(t_str)
                
                tax_val = t_val - f_val
                if tax_val > 0.01:
                    tax_amount = f"{tax_val:.2f}"
                    taxes.append({'codigo': 'TAX', 'monto': tax_amount, 'moneda': total_currency})
            except ValueError:
                pass

        # Normalizar fechas
        issue_date_iso = self.normalize_date(issue_date)
        
        # Normalizar nombre de aerolínea
        airline_normalized = self.normalize_airline_name(
            airline,
            flights[0].get('numero_vuelo') if flights else None,
            ticket_number=ticket_number
        )
        
        return ParsedTicketData(
            source_system='SABRE',
            pnr=pnr,
            ticket_number=ticket_number,
            passenger_name=passenger_name,
            passenger_document=document_id,
            issue_date=issue_date_iso or issue_date,
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
                'numero_iata': iata  # Alias for template compatibility
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
        """Extrae información de vuelos del texto"""
        flights = []
        
        # Extraer todas las horas del documento
        all_times = re.findall(r'\b(\d{1,2}:\d{2})\b', text)
        
        # Dividir por bloques de vuelo
        # Intentar extraer la sección de vuelos primero si el split global falla
        vuelo_section_match = re.search(r'(?:Información [Dd]e Vuelo|Flight Information)(.*?)(?:Detalles [Dd]e Pago|Payment Details|Aviso:|Notice:)', text, re.DOTALL | re.IGNORECASE)
        
        if vuelo_section_match:
            vuelo_text = vuelo_section_match.group(1)
            # Limpiar el texto de vuelos para quitar las líneas de 'No válido antes/después'
            # y las de emisión de CO2 antes de dividir
            vuelo_text = re.sub(r'(?:No válido|Not valid) (?:antes|después) del.*?\n', '', vuelo_text, flags=re.IGNORECASE)
            vuelo_text = re.sub(r'Est\. emission.*?\n', '', vuelo_text, flags=re.IGNORECASE)
            vuelo_text = re.sub(r'.*?KG CO2.*?\n', '', vuelo_text, flags=re.IGNORECASE)
            
            # Primero intentamos dividir por 'Preparado para' (que suele separar pasajeros)
            # NO dividimos por 'tarjeta de embarque' porque Sabre lo pone en medio de los vuelos.
            primary_blocks = re.split(r'(?:Preparado para|Prepared For)', vuelo_text, flags=re.IGNORECASE)
            
            flight_blocks = []
            for p_block in primary_blocks:
                if not p_block.strip(): continue
                # Dentro de cada bloque principal, buscamos dividir por fecha de vuelo (ej: 21dic20)
                # Esto es necesario si múltiples vuelos están listados uno tras otro antes del aviso
                # Regex busca: Salto de línea O Inicio de String + Fecha (DDMMMYY o similar)
                # FIX: Usamos (?:\n|^) para atrapar el primer vuelo si está al principio del bloque
                # FIX 2: Soportar prefijo "Salida:" si existe, y espacios antes de él
                date_split = re.split(r'((?:\n|^)\s*(?:Salida:\s*)?\s*\d{1,2}\s*[a-zA-Z]{3,}\s*\d{2,4})', p_block, flags=re.IGNORECASE)
                
                if len(date_split) > 1:
                     # Recombinar la fecha con su contenido posterior
                     # date_split[0] es basura antes de la primera fecha
                     # date_split[1] es fecha 1, date_split[2] es contenido 1...
                     for i in range(1, len(date_split), 2):
                         full_segment = date_split[i] + (date_split[i+1] if i+1 < len(date_split) else "")
                         flight_blocks.append(full_segment)
                else:
                    # Si no hay fechas claras, agregar el bloque entero
                    flight_blocks.append(p_block)
            
        else:
            flight_blocks = [] 
        
        valid_blocks = []
        for block in flight_blocks:
            block = block.strip()
            # Si el bloque parece ser el encabezado, saltarlo
            if re.search(r'(?:Prepared For|Preparado para|Monto Total|Total Amount)', block, re.IGNORECASE):
                continue
            
            # Filtro básico: debe tener codigo aerolínea + numero (XX 1234)
            if not block or not re.search(r'\b[A-Z0-9]{2}\s?\d{1,4}\b', block):
                continue
                
            # Si el bloque es solo ruido de CO2
            if 'KG CO2' in block.upper() or 'EST. EMISSION' in block.upper():
                 # A veces el CO2 está pegado al vuelo, mejor limpiarlo dentro del parseo
                 # Pero si el bloque ES SOLO eso, next
                 if len(block) < 50: continue
            
            valid_blocks.append(block)

        for block in valid_blocks:

            
            flight = {}
            lines = [line.strip() for line in block.splitlines() if line.strip()]
            
            # Buscar número de vuelo
            for i, line in enumerate(lines):
                match = re.search(r'\b([A-Z0-9]{2}\s*\d{1,4})\b', line)
                if match:
                    flight['numero_vuelo'] = match.group(1).replace(' ', '')
                    
                    # Buscar aerolínea en líneas anteriores
                    airline_parts = []
                    for j in range(i - 1, max(-1, i - 3), -1):
                        prev_line = lines[j]
                        # Detener si encontramos una fecha, una coma (ciudad), o si la línea parece una ciudad (mayúsculas)
                        if re.search(r'\d{2}\s+\w{3}\s+\d{2}', prev_line) or ',' in prev_line or re.search(r'^[A-Z\s]{3,}$', prev_line):
                            break
                        airline_parts.insert(0, prev_line)
                    
                    if airline_parts:
                        raw_airline = ' '.join(airline_parts)
                        flight['aerolinea'] = self.normalize_airline_name(
                            raw_airline,
                            flight.get('numero_vuelo')
                        )
                    
                    if not flight.get('aerolinea') or flight.get('aerolinea') == 'Aerolínea Desconocida':
                        # Fallback: Inferir desde el código de vuelo
                        flight['aerolinea'] = self.normalize_airline_name(
                            "",
                            flight.get('numero_vuelo')
                        )
                    break
            
            if not flight.get('numero_vuelo'):
                continue
            
            # Si no se encontró aerolínea por líneas, buscar en el mismo bloque nombres conocidos
            if not flight.get('aerolinea') or flight.get('aerolinea') == 'Aerolínea Desconocida':
                known_airlines = {
                    'AF ': 'Air France',
                    'AV ': 'Avianca',
                    'CM ': 'Copa Airlines',
                    'AA ': 'American Airlines',
                    'IB ': 'Iberia',
                    'UX ': 'Air Europa',
                    'LA ': 'LATAM',
                }
                for code, name in known_airlines.items():
                    if code in block or name.upper() in block.upper():
                        flight['aerolinea'] = name
                        break
            
            # Extraer fechas (Soporta 19nov20 o 19 nov 20)
            date_match = re.search(r'(\d{1,2}\s*\w{3}\s*\d{2,4})', block)
            if date_match:
                flight['fecha_salida'] = date_match.group(1)
            
            arrival_match = re.search(r'(Llegada|Arrival):\s*(\d{1,2}\s+\w{3}\s+\d{2})', block)
            if arrival_match:
                flight['fecha_llegada'] = arrival_match.group(2)
            else:
                flight['fecha_llegada'] = None
            
            # Extraer horas
            if all_times:
                flight['hora_salida'] = all_times.pop(0)
            if all_times:
                flight['hora_llegada'] = all_times.pop(0)
            
            # Cargar aerolínea y código para limpieza
            airline_name = flight.get('aerolinea', '')
            flight_num = flight.get('numero_vuelo', '')
            airline_code = flight_num[:2] if flight_num else ''

            # Limpiar el bloque para buscar ciudades
            clean_block = block
            
            # 1. Quitar líneas de metadatos conocidas de Sabre
            labels_to_remove = [
                r'Código de reservación.*', r'la aerolínea.*', r'Terminal.*',
                r'Límite de equipaje.*', r'Base de tarifa.*', r'Estado de la reservación.*',
                r'No válido.*', r'Operado por.*', r'Número de asiento.*', r'Hora.*',
                r'Esta no es una tarjeta.*', r'Not valid.*', r'Seat number.*',
                r'Baggage Allowance.*', r'Reservation Status.*', r'LINEAS', r'AEREAS'
            ]
            for label in labels_to_remove:
                clean_block = re.sub(label, '', clean_block, flags=re.IGNORECASE)

            # 2. Quitar aerolínea y código del bloque para no confundirlos con ciudades
            if airline_name:
                # Usar regex para manejar espacios múltiples
                pattern = re.escape(airline_name).replace(r'\ ', r'\s+')
                clean_block = re.sub(pattern, '', clean_block, flags=re.IGNORECASE)
            if airline_code:
                clean_block = re.sub(r'\b' + re.escape(airline_code) + r'\b', '', clean_block, flags=re.IGNORECASE)
            
            # --- ESTRATEGIA DE CIUDADES (MEJORADA PARA TEXTO SCRAMBLED) ---
            # En Sabre PDF, el origen y destino suelen estar en la línea de 'Salida'
            # después de la fecha y la aerolínea.
            
            origin = "No encontrado"
            destination = "No encontrado"
            
            # Limpiar la línea de Salida (y el resto del bloque para manejar saltos de línea)
            # FIX: Usamos todo el bloque desde "Salida:" en adelante para capturar ciudades multi-línea
            # FIX: Si NO hay "Salida:", usamos el bloque entero (para evitar variable leak del vuelo anterior)
            # FIX: Usamos todo el bloque desde "Salida:" en adelante para capturar ciudades multi-línea
            # FIX: Si NO hay "Salida:", usamos el bloque entero (para evitar variable leak del vuelo anterior)
            match_salida = re.search(r'((?:Salida|Departure|Depart):.*)', clean_block, re.IGNORECASE | re.DOTALL)
            if match_salida:
                s_clean = match_salida.group(1)
                # Quitar "Salida:", fecha
                s_clean = re.sub(r'(?:Salida|Departure|Depart):.*?(\d{1,2}\s+\w{3}\s+\d{2,4})', '', s_clean, flags=re.IGNORECASE)
            else:
                s_clean = clean_block
                
            if airline_name:
                s_clean = re.sub(re.escape(airline_name), '', s_clean, flags=re.IGNORECASE)
            if airline_code:
                s_clean = re.sub(r'\b' + re.escape(airline_code) + r'\b', '', s_clean, flags=re.IGNORECASE)
            
            # Quitar etiquetas de metadatos al final
            s_clean = re.sub(r'(?:Código de reservación|RESERVATION CODE).*', '', s_clean, flags=re.IGNORECASE)
            s_clean = re.sub(r'Terminal.*', '', s_clean, flags=re.IGNORECASE)
            s_clean = re.sub(r'aerol[íi]nea\s*[A-Z0-9]{6}\b', '', s_clean, flags=re.IGNORECASE) # Quitar localizador local
            # Limpieza de Nombres Legales largos que ensucian el origen/destino
            legal_noise = [
                'LINEAS', 'AEREAS', 'AEROVIAS', 'DEL', 'CONTINENTE', 
                'COMPANIA', 'PANAMENA', 'DE', 'AVIACION', 
                'INTERNATIONAL', 'AIRLINES', 'SATA', 'SERVICES', 
                'ARGENTINAS', 'ARGENTINA', 'LTD', 'INC', 'S.A.',
                'GOL', 'LINHAS'
            ]
            for noise_word in legal_noise:
                s_clean = re.sub(r'\b' + re.escape(noise_word) + r'\b', '', s_clean, flags=re.IGNORECASE)
                
                # Buscar ciudades con comas: Mejorado para no ser tan codicioso
            # Limitamos los espacios después de la coma para atrapar solo una palabra del país
            # FIX: Hacemos el país opcional (MATCH GROUP 2) y removemos \b final para soportar fin de string o comas
                
            # FIX: Usar lógica de "Anchor-Gap" para evitar que la Ciudad 2 sea consumida como País de la Ciudad 1
            # "SHANGHAI PUDONG, PARIS DE GAULLE" -> Gap entre "PUDONG," y "PARIS" es vacío (o espacios).
            
            anchor_regex = r'\b([A-ZÁÉÍÓÚ]{3,}(?:\s+[A-ZÁÉÍÓÚ]+)*),'
            matches = list(re.finditer(anchor_regex, s_clean))
            found_cities = []
            
            for i, m in enumerate(matches):
                city_raw = m.group(1)
                start_match = m.start()
                
                # Check previous gap for country (Standard Case: "City, Country NextCity,")
                # Need to calculate gap from previous match end to current match start?
                # Actually, if regex consumed the country, it's in city_raw.
                
                # Logic: Check if city_raw starts with a known country
                clean_city_raw = city_raw.replace('\n', ' ').strip()
                
                COMMON_COUNTRIES = [
                    'SPAIN', 'FRANCE', 'COLOMBIA', 'CHINA', 'USA', 'UK', 'GERMANY', 'ITALY', 
                    'VENEZUELA', 'UNITED STATES', 'ARGENTINA', 'MEXICO', 'PANAMA', 'PERU', 
                    'CHILE', 'ECUADOR', 'BRASIL', 'BRAZIL', 'CANADA', 'JAPAN', 'KOREA',
                    'NJ', 'NY', 'FL', 'TX', 'CA', 'IL', 'MA'
                ]
                
                country_peeled = None
                real_city = clean_city_raw
                
                # Only peel if we have a previous city that needs a country
                if i > 0:
                    gap_parts = clean_city_raw.split(' ', 1)
                    first_word = gap_parts[0].upper()
                    
                    is_united_states = (first_word == 'UNITED' and len(gap_parts)>1 and gap_parts[1].upper().startswith('STATES'))
                    
                    if first_word in COMMON_COUNTRIES or is_united_states:
                         if is_united_states:
                             country_peeled = "UNITED STATES"
                             real_city = gap_parts[1][6:].strip() # Remove STATES...
                         else:
                             country_peeled = first_word
                             real_city = gap_parts[1].strip() if len(gap_parts) > 1 else ""
                             
                         # Assign peeled country to PREVIOUS city
                         # found_cities is list of [city, country]
                         if not found_cities[-1][1]: # Only if it doesn't have one
                             found_cities[-1][1] = country_peeled
                             
                # Now verify if there is a country in the GAP AFTER this city
                start_gap = m.end()
                end_gap = matches[i+1].start() if i+1 < len(matches) else len(s_clean)
                gap = s_clean[start_gap:end_gap].strip()
                country_forward = None
                
                if len(gap) > 1:
                    clean_gap = re.sub(r'[\r\n\t]+', ' ', gap).strip()
                    first_token = clean_gap.split()[0].rstrip(',.').upper()
                    
                    # 1. Check against Known Countries
                    if first_token in COMMON_COUNTRIES:
                        country_forward = first_token
                    # 2. Check for UNITED STATES
                    elif first_token == 'UNITED' and 'STATES' in clean_gap.upper():
                        country_forward = "UNITED STATES"
                    # 3. Fallback: Strict Alpha check (Short)
                    elif re.match(r'^[A-ZÁÉÍÓÚ\s]+$', clean_gap) and len(clean_gap) < 20:
                         country_forward = clean_gap

                found_cities.append([real_city, country_forward])

            if len(found_cities) >= 2:
                # found_cities es una lista de tuplas (Ciudad, Pais_Opcional)
                origin_city, origin_country = found_cities[0]
                dest_city, dest_country = found_cities[1]
                
                origin = origin_city
                if origin_country:
                    origin += f", {origin_country}"
                    
                destination = dest_city
                if dest_country:
                    destination += f", {dest_country}"
            elif len(found_cities) == 1 and origin == "No encontrado":
                origin_city, origin_country = found_cities[0]
                origin = origin_city
                
                # FIX LOGIC: Remove CITY and COUNTRY
                remaining = s_clean.replace(origin, '').replace(',', '')
                if origin_country:
                    remaining = remaining.replace(origin_country, '')
                remaining = remaining.strip()
                
                # Buscar blocks de mayúsculas que NO sean metadatos
                dest_blocks = re.findall(r'\b([A-ZÁÉÍÓÚ\s]{3,})\b', remaining)
                # No excluir ciudades que podrían ser el destino
                dest_candidates = [b.strip() for b in dest_blocks if len(b.strip()) > 2 and not any(n in b.upper() for n in ['SALIDA', 'LLEGADA', 'AIR', 'AEROLINEA'])]
                if dest_candidates:
                    destination = dest_candidates[0]
            else:
                # Sin comas, buscar por bloques de mayúsculas
                blocks = re.findall(r'\b([A-ZÁÉÍÓÚ\s]{3,})\b', s_clean)
                blocks = [b.strip() for b in blocks if len(b.strip()) > 3 and not any(n in b.upper() for n in ['SALIDA', 'AIR', 'FRANCE', 'AVIANCA', 'BOGOTA'])]
                if len(blocks) >= 2:
                    origin = blocks[0]
                    destination = blocks[1]

            
            # Si no se encontró destino en la línea de Salida, buscar en el bloque entero
            if destination == "No encontrado" or any(n in destination.upper() for n in ['REQUIERE', 'CHECK']):
                # Buscar patrones "CIUDAD, PAIS" en todo el bloque (excluyendo lo que ya sabemos que es ruido)
                all_cities = re.findall(r'([A-ZÁÉÍÓÚ\s]{3,},\s*[A-ZÁÉÍÓÚ\s]{3,})', clean_block)
                if len(all_cities) >= 2:
                    origin = all_cities[0]
                    destination = all_cities[1]
                elif len(all_cities) == 1 and origin == "No encontrado":
                     origin = all_cities[0]

            # Limpieza final de ciudades
            noise_to_strip = [
                'TERMINAL', 'CABINA', 'TURISTA', 'PREMIUM', 'REQUIERE', 'CHECK',
                'OPERADO', 'HORA', 'ESTADO', 'CONFIRMADO', 'AEROGARE', 'TERM'
            ]
            
            def clean_city(c):
                if not c: return "No encontrado"
                for n in noise_to_strip:
                    c = re.sub(r'\b' + n + r'\b.*', '', c, flags=re.IGNORECASE).strip()
                # Quitar comas colgadas al final
                c = re.sub(r',\s*$', '', c).strip()
                return c if len(c) > 2 else "No encontrado"

            origin = clean_city(origin)
            destination = clean_city(destination)


            
            if origin != "No encontrado":
                parts = origin.split(',')
                flight['origen'] = {
                    'ciudad': self.clean_text(parts[0]),
                    'pais': None # Simplificado por solicitud
                }
            
            if destination != "No encontrado":
                parts = destination.split(',')
                flight['destino'] = {
                    'ciudad': self.clean_text(parts[0]),
                    'pais': None # Simplificado por solicitud
                }
            
            # --- FIN ESTRATEGIA CIUDADES ---
            
            # Otros detalles
            cabin_match = re.search(r'Cabina\s+([A-Za-z]+)', block, re.IGNORECASE)
            if cabin_match:
                flight['cabina'] = cabin_match.group(1)
            
            # Regex Equipaje Mejorado
            bag_match = re.search(r'(?:Límite de equipaje|Baggage Allowance|Equipaje|Franquicia)[:\s]*(?:\n)?\s*([0-9]+\s*(?:PC|KG)|[0-9]+PC)', block, re.IGNORECASE)
            if bag_match:
                flight['equipaje'] = bag_match.group(1).replace(' ', '')
            
            # Agregar localizador de aerolínea si existe
            # Buscar patrón: aerolínea XXXXXX (6 chars)
            # El texto raw muestra "UA 1052 aerolÝnea PG0E4P"
            pnr_match = re.search(r'(?:aerol[íi]nea|aerolÝnea)\s*([A-Z0-9]{6})\b', block, re.IGNORECASE)
            if pnr_match:
                flight['codigo_reservacion_local'] = pnr_match.group(1)
            else:
                # Fallback: Buscar código de 6 letras mayúsculas/números cerca del numero de vuelo
                # a veces solo aparece "UA1052 XXXXXX"
                # Pero cuidado de no capturar el mismo vuelo o fechas
                pass
            
            flight['codigo_reservacion_local'] = flight.get('codigo_reservacion_local', "No encontrado")
            
            flights.append(flight)

        # Propagación de Equipaje: Si falta en alguno, usar el de otro vuelo del mismo boleto
        known_baggage = next((f.get('equipaje') for f in flights if f.get('equipaje')), None)
        if known_baggage:
            for f in flights:
                if not f.get('equipaje'):
                    f['equipaje'] = known_baggage

        return flights

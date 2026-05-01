# -*- coding: utf-8 -*-
import logging
import hashlib
import re
from typing import Dict, Any, Optional
from django.core.cache import cache

logger = logging.getLogger(__name__)

class FastDeterministicParsers:
    """
    🛡️ EL ESCUDO DETERMINÍSTICO (Regex)
    Reglas de extracción rápidas y gratuitas para cuando la IA falla o para ahorrar costos.
    """
    
    @staticmethod
    def parse_general_regex(text: str) -> Dict[str, Any]:
        """
        Intenta extraer lo básico (Nombre, PNR, Ticket, Itinerario) usando patrones comunes.
        """
        data = {'flights': []}
        text_upper = text.upper()

        # 1. Extraer PNR / Localizador (GDS)
        # Soporta acentos (Ó) y el símbolo +
        pnr_match = re.search(r'(?:RESERVACI[OÓ]N|RESERVA|CODE|PNR|LOCALIZADOR|RECORD|BOOKING REF)[:\s\n]+([A-Z0-9]{6,8})', text_upper)
        if pnr_match:
            data['codigo_reserva'] = pnr_match.group(1).replace('+', '') 

        # 1b. Extraer PNR de Aerolínea (Específico)
        # Buscamos patrones como "CÓDIGO DE RESERVACIÓN DE LA AEROLÍNEA" o "AIRLINE CONFIRMATION"
        # Usamos re.sub para normalizar espacios y saltos de línea antes de buscar.
        normalized_text = re.sub(r'\s+', ' ', text_upper)
        air_pnr_patterns = [
            r'(?:C[OÓ]DIGO\s+DE\s+)?RESERVACI[OÓ]N\s+DE\s+LA\s+AEROL[IÍ]NEA[:\s]+([A-Z0-9]{6})',
            r'(?:C[OÓ]DIGO\s+DE\s+)?RESERVA\s+DE\s+LA\s+AEROL[IÍ]NEA[:\s]+([A-Z0-9]{6})',
            r'AIRLINE\s+RESERVATION\s+CODE[:\s]+([A-Z0-9]{6})',
            r'CONFIRMACI[OÓ]N\s+AEROL[IÍ]NEA[:\s]+([A-Z0-9]{6})',
            r'AIRLINE\s+CONFIRMATION[:\s]+([A-Z0-9]{6})'
        ]
        
        for pattern in air_pnr_patterns:
            air_match = re.search(pattern, normalized_text)
            if air_match:
                pnr_val = air_match.group(1).strip()
                data['pnr_aerolinea'] = pnr_val
                data['airline_pnr'] = pnr_val
                break
        
        # Reintento si falló (Búsqueda más agresiva)
        if 'airline_pnr' not in data:
            # Patrón para: Código de reservación de la aerolínea ABCDEF
            aggressive_match = re.search(r'RESERVACI[OÓ]N\s+DE\s+LA\s+AEROL[IÍ]NEA\s+([A-Z0-9]{6})', normalized_text)
            if aggressive_match:
                data['airline_pnr'] = aggressive_match.group(1)

        # 2. Extraer Número de Boleto (13 dígitos)
        tkt_match = re.search(r'(?:BOLETO|TICKET|ETKT|NUMERO|TKTN)[:\s]+(?:235-?)?([0-9]{10,13})', text_upper)
        if tkt_match:
            tkt = tkt_match.group(1)
            if len(tkt) == 10: tkt = "235" + tkt # Turkish Prefix if missing
            data['numero_boleto'] = tkt

        # 3. Extraer Nombre del Pasajero y Documento
        # Soporta: NOMBRE [DOCUMENTO]
        name_match = re.search(r'(?:PREPARADO PARA|PASAJERO|PASSENGER|NAME|PAX)[:\s]+([^[\n\r<]{3,50})(?:\[([^\]]+)\])?', text_upper)
        if name_match:
            raw_name = name_match.group(1).strip()
            data['nombre_pasajero'] = raw_name
            if name_match.group(2):
                data['foid'] = name_match.group(2).strip()

        # 4. Extraer Aerolínea
        if "TURKISH" in text_upper:
            data['aerolinea_emisora'] = "TURKISH AIRLINES"
        elif "LASER" in text_upper:
            data['aerolinea_emisora'] = "LASER AIRLINES"
        elif "COPA" in text_upper:
            data['aerolinea_emisora'] = "COPA AIRLINES"

        # 5. Extraer Fecha de Emisión
        date_match = re.search(r'(?:EMISION|ISSUED|DATE|FECHA)[:\s]+(\d{1,2}\s+[A-Z]{3}\s+\d{2,4})', text_upper)
        if date_match:
            data['fecha_emision'] = date_match.group(1)
        else:
            # Reintento para formato abreviado (29 ABR 26)
            date_match = re.search(r'(\d{1,2}\s+[A-Z]{3}\s+\d{2})', text_upper)
            if date_match: data['fecha_emision'] = date_match.group(1)

        # 6. Extraer Itinerario (Vuelos) - Motor de Segmentos GDS Pro (Audit Point 2)
        # Patrón mejorado para Sabre/Amadeus:
        # Ejemplo: 1  AV 46   C 22MAY 4 BOGMAD HK1  0700   2330   *E
        # Grupos: 1:Aerolinea, 2:Vuelo, 3:Clase, 4:Fecha, 5:Origen, 6:Destino, 7:Status, 8:Salida, 9:Llegada
        flight_pattern = re.compile(
            r'(?:\d+\s+)?'                          # Index opcional (1 )
            r'([A-Z0-9]{2})\s+'                     # Aerolinea (AV)
            r'(\d{1,4})\s+'                         # Numero de vuelo (46)
            r'([A-Z])?\s*'                          # Clase (C) opcional
            r'(\d{2}[A-Z]{3})\s+'                   # Fecha (22MAY)
            r'(?:\d\s+)?'                           # Día de semana opcional (4 )
            r'([A-Z]{3})([A-Z]{3})\s+'              # OrigenDestino (BOGMAD)
            r'([A-Z0-9]{2,3})\s+'                   # Status (HK1)
            r'(\d{2}:?\d{2})\s+(\d{2}:?\d{2})'      # Salida (0700) Llegada (2330)
        )
        
        matches = flight_pattern.findall(text_upper)
        
        for m in matches:
            # Normalizar horas
            dep_time = f"{m[7][:2]}:{m[7][2:]}" if ':' not in m[7] else m[7]
            arr_time = f"{m[8][:2]}:{m[8][2:]}" if ':' not in m[8] else m[8]

            flight = {
                'airline': m[0],
                'flightNumber': f"{m[0]} {m[1]}",
                'date': m[3],
                'departure': {'location': m[4], 'time': dep_time},
                'arrival': {'location': m[5], 'time': arr_time},
                'status': m[6] or 'CONFIRMADO',
                # Compatibilidad
                'origen': m[4],
                'destino': m[5],
                'vuelo': f"{m[0]} {m[1]}",
                'fecha_salida': m[3],
                'hora_salida': dep_time,
                'hora_llegada': arr_time
            }
            data['flights'].append(flight)
            
        # 7. Reintento específico para Turkish Airlines (Formato multi-línea)
        if not data['flights']:
            # Buscamos bloques que empiecen con fecha y aerolínea
            # Ejemplo: 12 may 26 TURKISH AIRLINES SHANGHAI PUDONG, ISTANBUL AIRPORT ... TK 281
            tk_blocks = re.split(r'(\d{1,2}\s+[A-Z]{3}\s+\d{2,4}\s+TURKISH AIRLINES)', text_upper)
            if len(tk_blocks) > 1:
                for i in range(1, len(tk_blocks), 2):
                    header = tk_blocks[i]
                    content = tk_blocks[i+1] if i+1 < len(tk_blocks) else ""
                    
                    date_match = re.search(r'(\d{1,2}\s+[A-Z]{3}\s+\d{2,4})', header)
                    loc_match = re.search(r'TURKISH AIRLINES\s+([^,]+),\s+([^\n,]+)', header + content)
                    fn_match = re.search(r'TK\s*(\d{1,4})', content)
                    
                    # Localizador de aerolínea (UQZIPR) - Soporta multi-línea
                    # Patrones específicos para Sabre: "CÓDIGO DE RESERVACIÓN DE LA AEROLÍNEA" o similares
                    air_pnr_match = re.search(r'(?:RESERVACI[OÓ]N\s+DE\s+LA\s+AEROL[IÍ]NEA|AIRLINE\s+CONFIRMATION|C[OÓ]DIGO\s+DE\s+RESERVACI[OÓ]N\s+DE\s+LA\s+AEROL[IÍ]NEA)[:\s\n]+([A-Z0-9]{6})', content.replace('\n', ' '))
                    if not air_pnr_match:
                         # Intento con el texto largo "reservación de la aerolínea"
                         air_pnr_match = re.search(r'RESERVACI[OÓ]N\s+DE\s+LA\s+AEROL[IÍ]NEA\s+([A-Z0-9]{6})', content.replace('\n', ' '))
                    if not air_pnr_match:
                         # Intento genérico para AIRLINE PNR
                         air_pnr_match = re.search(r'(?:AEROL[IÍ]NEA|AIRLINE)[:\s\n]+([A-Z0-9]{6})', content)
                    
                    # Horas (07:55 14:50)
                    times_match = re.search(r'(\d{2}:\d{2})\s+(\d{2}:\d{2})', content)
                    
                    if date_match and loc_match and fn_match:
                         data['flights'].append({
                            'airline': 'TURKISH AIRLINES',
                            'flightNumber': f"TK {fn_match.group(1)}",
                            'date': date_match.group(1),
                            'origen': loc_match.group(1).strip(),
                            'destino': loc_match.group(2).strip(),
                            'departure': {
                                'location': loc_match.group(1).strip(), 
                                'time': times_match.group(1) if times_match else '--'
                            },
                            'arrival': {
                                'location': loc_match.group(2).strip(), 
                                'time': times_match.group(2) if times_match else '--'
                            },
                            'airline_pnr': air_pnr_match.group(1) if air_pnr_match else '',
                            'status': 'CONFIRMADO'
                        })

        return data

def extract_data_from_text(plain_text: str, html_text: str = "", pdf_path: Optional[str] = None, bypass_cache: bool = False) -> Dict[str, Any]:
    """
    Orquestador Híbrido: Caché -> Regex -> IA (God Mode)
    """
    if not plain_text:
        return {"error": "Texto vacío"}

    # 1. 🧱 CACHÉ (Evita procesar dos veces lo mismo)
    fingerprint = hashlib.sha256(plain_text.encode('utf-8')).hexdigest()
    cache_key = f"parser:doc:{fingerprint}"
    
    if not bypass_cache:
        cached_result = cache.get(cache_key)
        if cached_result:
            logger.info(f"💾 Usando resultado cacheado para doc {fingerprint}")
            return cached_result

    # 2. ⚡ PATRONES DETERMINÍSTICOS (Gratis y Rápidos)
    # Siempre intentamos extraer lo básico primero
    res_final = FastDeterministicParsers.parse_general_regex(plain_text)
    
    # Si tenemos lo básico (PNR y Nombre), podemos considerarlo un éxito parcial
    has_basics = res_final.get('codigo_reserva') and res_final.get('nombre_pasajero')

    # 3. 🧠 INTELIGENCIA ARTIFICIAL (DELEGADO AL SERVICIO SUPERIOR)
    # Ya no llamamos a AIParserService aquí para evitar duplicidad de costos y errores.
    # El TicketParserService se encargará de llamar a UniversalAIParser si es necesario.
    pass

    # 4. 💾 GUARDAR EN CACHÉ
    if res_final and (res_final.get('codigo_reserva') or res_final.get('nombre_pasajero')):
        cache.set(cache_key, res_final, timeout=86400 * 30)

    return res_final

def is_brand_color_dark(hex_color: str) -> bool:
    if not hex_color or not isinstance(hex_color, str): return True
    hex_color = hex_color.lstrip('#')
    if len(hex_color) != 6: return True
    try:
        r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        luma = 0.299 * r + 0.587 * g + 0.114 * b
        return luma < 128
    except: return True


def _parse_date_robust(date_str):
    """
    Intenta parsear fechas en formatos comunes de GDS (25APR, 25 APR 2024, etc)
    """
    if not date_str or str(date_str).strip() == "":
        return None
        
    date_str = str(date_str).upper().strip()
    # Limpieza de ruidos comunes
    date_str = re.sub(r'^(?:EMISION|ISSUED|DATE|FECHA)[:\s]+', '', date_str)
    
    # Diccionario de meses en español
    meses_es = {
        'ENE': 'JAN', 'FEB': 'FEB', 'MAR': 'MAR', 'ABR': 'APR', 'MAY': 'MAY', 'JUN': 'JUN',
        'JUL': 'JUL', 'AGO': 'AUG', 'SEP': 'SEP', 'OCT': 'OCT', 'NOV': 'NOV', 'DIC': 'DEC'
    }
    for es, en in meses_es.items():
        if es in date_str:
            date_str = date_str.replace(es, en)

    from datetime import datetime
    import locale
    
    formatos = [
        "%d%b", "%d %b", "%d %b %Y", "%d%b%y", "%d%b%Y",
        "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"
    ]
    
    # Intentar con meses en inglés (estándar GDS)
    for fmt in formatos:
        try:
            dt = datetime.strptime(date_str, fmt)
            # Si no tiene año, asumimos el actual o el próximo según el mes
            if dt.year == 1900:
                now = datetime.now()
                dt = dt.replace(year=now.year)
                # Si el mes ya pasó hace mucho (ej: estamos en Dic y la fecha es Ene), 
                # podría ser del año que viene, pero para emisión solemos usar el actual.
            return dt.date()
        except:
            continue
            
    return None

def generate_ticket(data: Dict[str, Any], agencia_obj=None, boleto_obj=None):
    from core.services.parsers.pdf_generation import PdfGenerationService
    # Siempre pasamos el objeto de boleto si viene en la data para asegurar persistencia
    return PdfGenerationService.generate_ticket(data, agencia_obj, boleto_obj=boleto_obj or data.get('_boleto_instance'))
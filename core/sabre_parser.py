# c:\Users\ARMANDO\travelhub_project\core\sabre_parser.py

import re
import logging
from typing import Any, Dict, List

# Importar funciones auxiliares de parsing_utils para centralizar la lógica
from .parsing_utils import (
    _extract_field,
    _parse_currency_amount,
    _formatear_fecha_dd_mm_yyyy,
    _inferir_fecha_llegada,
    _fecha_a_iso
)
from .airline_utils import normalize_airline_name

logger = logging.getLogger(__name__)

def _parsear_itinerario_sabre(itinerario_texto: str, texto_completo: str) -> List[Dict[str, Any]]:
    """Refactorización v10: Lógica de aerolínea multi-línea mejorada."""
    vuelos: List[Dict[str, Any]] = []
    if not itinerario_texto:
        return vuelos

    all_times = re.findall(r'(?:Time|Hora)\s*(\d{1,2}:\d{2})', texto_completo)
    flight_blocks = re.split(r'This is not a boarding pass|Esta no es una tarjeta de embarque', itinerario_texto)

    for bloque in flight_blocks:
        b = bloque.strip()
        if not b or not re.search(r'\b[A-Z]{2}\s?\d{1,4}\b', b):
            continue

        vuelo: Dict[str, Any] = {}
        lines = [line.strip() for line in b.splitlines() if line.strip()]
        flight_line_index = -1

        # 1. ANCHOR: Find the flight number line
        for i, line in enumerate(lines):
            match_vuelo = re.search(r'\b([A-Z]{2}\s*\d{1,4})\b', line)
            if match_vuelo:
                flight_line_index = i
                vuelo['numero_vuelo'] = match_vuelo.group(1).replace(' ', '')
                break
        
        if flight_line_index == -1:
            continue

        # 2. AIRLINE: Reconstruct name by walking backwards from the anchor
        airline_parts = []
        for j in range(flight_line_index - 1, -1, -1):
            prev_line = lines[j]
            # Stop if the line looks like a date, city, or is too long
            if re.search(r'\d{2}\s+\w{3}\s+\d{2}', prev_line) or ',' in prev_line or len(prev_line) > 30:
                break
            airline_parts.insert(0, prev_line)
        if airline_parts:
            raw_airline = ' '.join(airline_parts)
            vuelo['aerolinea'] = normalize_airline_name(raw_airline, vuelo.get('numero_vuelo'))

        # 3. DATES (Flexible)
        m_fecha = re.search(r'(\d{1,2}\s+\w{3}\s+\d{2})', b)
        if m_fecha:
            vuelo['fecha_salida'] = m_fecha.group(1)

        m_fecha_llegada = re.search(r'(Llegada|Arrival):\s*(\d{1,2}\s+\w{3}\s+\d{2})', b)
        if m_fecha_llegada:
            vuelo['fecha_llegada'] = m_fecha_llegada.group(2)
        else:
            vuelo['fecha_llegada'] = None

        # 4. HORAS
        if all_times: vuelo['hora_salida'] = all_times.pop(0)
        if all_times: vuelo['hora_llegada'] = all_times.pop(0)

        # 5. ORIGEN Y DESTINO
        b_normalized = re.sub(r'(,\s*)\n', r', ', b)
        ciudades = re.findall(r'([A-ZÁÉÍÓÚ -]+,\s*[A-ZÁÉÍÓÚ -]+)', b_normalized)
        ciudades_validas = [c for c in ciudades if "DORAL" not in c.upper()]
        if len(ciudades_validas) >= 2:
            origin_parts = ciudades_validas[0].split(',')
            dest_parts = ciudades_validas[1].split(',')
            vuelo['origen'] = {'ciudad': origin_parts[0].strip(), 'pais': origin_parts[1].strip() if len(origin_parts) > 1 else None}
            vuelo['destino'] = {'ciudad': dest_parts[0].strip(), 'pais': dest_parts[1].strip() if len(dest_parts) > 1 else None}

        # 6. OTROS DETALLES
        m_cabin = re.search(r'Cabina\s+([A-Za-z]+)', b, re.IGNORECASE)
        if m_cabin: vuelo['cabina'] = m_cabin.group(1)
        
        m_bag = re.search(r'(?:Límite de equipaje|Baggage Allowance)\s*([A-Z0-9]+)', b, re.IGNORECASE)
        if m_bag: vuelo['equipaje'] = m_bag.group(1)

        m_pnr = re.search(r'(?:Código de reservación de la aerolínea|Airline Reservation Code)\s*([A-Z0-9]+)', b, re.IGNORECASE)
        if m_pnr: vuelo['codigo_reservacion_local'] = m_pnr.group(1)

        if vuelo.get('numero_vuelo'):
            vuelos.append(vuelo)

    return vuelos

def parse_sabre_ticket(plain_text: str) -> Dict[str, Any]:
    """Parsea el contenido de un boleto Sabre y devuelve un diccionario estructurado."""
    logger.info("Iniciando parseo de boleto Sabre con lógica v10.")
    
    nombre_pasajero = _extract_field(plain_text, [r'(?:Prepared For|Preparado para)\s*\n\s*([A-ZÁÉÍÓÚ0-9\-\/\[\s,\.]+?)(?:\s*\[|\n|$)' ], default='')
    documento_identidad = _extract_field(plain_text, [r'(?:Prepared For|Preparado para)\s*[A-ZÁÉÍÓÚ/\s]+\s*\[([A-Z0-9]+)\]'], default='')
    codigo_reservacion = _extract_field(plain_text, [r'(?:Reservation Code|C[ÓO]DIGO DE RESERVACIÓN)\s*[:\t\s]*([A-Z0-9]+)'], default='')
    fecha_emision = _extract_field(plain_text, [r'(?:Issue Date|Fecha de Emisi[oó]n|FECHA DE EMISIÓN)\s*[:\t\s]*([\d]{1,2}\s+\w{3}\s+[\d]{2})'], default='')
    numero_boleto = _extract_field(plain_text, [r'(?:Ticket Number|N[ÚU]MERO DE BOLETO)\s*[:\t\s]*([\d]+)'], default='')
    aerolinea_emisora = _extract_field(plain_text, [r'(?:Issuing Airline|AEROL[ÍI]NEA EMISORA)\s*[:\t\s]*([A-ZÁÉÍÓÚ0-9 \/]+)'], default='')
    agente_emisor_raw = _extract_field(plain_text, [r'(?:Issuing Agent|AGENTE EMISOR)\s*[:\t\s]*([^\n\r]+)'], default='')
    numero_iata = _extract_field(plain_text, [r'(?:IATA Number|IATA)\s*[:\t\s]*([\d]+)'], default='')
    numero_cliente = _extract_field(plain_text, [r'(?:Customer Number|Customer|N[ÚU]MERO DE CLIENTE)\s*[:\t\s]*([A-Z0-9]+)'], default='')

    agente_emisor = agente_emisor_raw.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ').split('Issuing Agent Location')[0].strip()

    itinerario_raw = _extract_field(plain_text, [
        r'Itinerary Details(.*?)(?=QUO VADIS TRAVEL AGENCY|Por favor contacte)',
        r'Información De Vuelo(.*?)(?=QUO VADIS TRAVEL AGENCY|Por favor contacte)'
    ], default='')
    
    vuelos = _parsear_itinerario_sabre(itinerario_raw, plain_text)

    fecha_emision_fmt = _formatear_fecha_dd_mm_yyyy(fecha_emision)
    fecha_emision_iso = _fecha_a_iso(fecha_emision_fmt) or _fecha_a_iso(fecha_emision)

    vuelos_fmt = []
    for v in vuelos:
        fs_raw = v.get('fecha_salida', '')
        fl_raw = v.get('fecha_llegada', '')
        hs = v.get('hora_salida')
        hl = v.get('hora_llegada')
        
        v['fecha_salida'] = _formatear_fecha_dd_mm_yyyy(fs_raw)
        v['fecha_llegada'] = _inferir_fecha_llegada(fs_raw, hs, hl, fl_raw)
        v['fecha_salida_iso'] = _fecha_a_iso(v['fecha_salida'])
        v['fecha_llegada_iso'] = _fecha_a_iso(v['fecha_llegada'])
        vuelos_fmt.append(v)

    fare_raw = _extract_field(plain_text, [r'Fare\s+([A-Z]{3}\s*[0-9,.]+)', r'Tarifa\s+([A-Z]{3}\s*[0-9,.]+)'], default='')
    total_raw = _extract_field(plain_text, [r'Total\s+([A-Z]{3}\s*[0-9,.]+)'], default='')
    
    fare_cur, fare_amt = _parse_currency_amount(fare_raw)
    total_cur, total_amt = _parse_currency_amount(total_raw)

    data = {
        'SOURCE_SYSTEM': 'SABRE_RESTORED',
        'pasajero': {
            'nombre_completo': nombre_pasajero,
            'documento_identidad': documento_identidad or None,
            'numero_cliente': numero_cliente or None,
        },
        'reserva': {
            'codigo_reservacion': codigo_reservacion,
            'numero_boleto': numero_boleto,
            'fecha_emision_iso': fecha_emision_iso,
            'aerolinea_emisora': normalize_airline_name(aerolinea_emisora, vuelos_fmt[0].get('numero_vuelo') if vuelos_fmt else None),
            'agente_emisor': {
                'nombre': agente_emisor,
                'numero_iata': numero_iata,
            },
        },
        'finanzas': {
            'fare_raw': fare_raw if fare_raw != 'No encontrado' else None,
            'fare_currency': fare_cur,
            'fare_amount': str(fare_amt) if fare_amt is not None else None,
            'total_raw': total_raw if total_raw != 'No encontrado' else None,
            'total_currency': total_cur,
            'total_amount': str(total_amt) if total_amt is not None else None,
        },
        'itinerario': {
            'vuelos': vuelos_fmt,
        },
        'errores': []
    }

    return data

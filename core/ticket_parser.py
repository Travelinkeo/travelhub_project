# Archivo: core/ticket_parser.py

import re
import logging
from .identification_utils import normalize_codigo_identificacion, extract_codigo_identificacion_anywhere
from .utils import LOCATION_TOKENS, STOP_NAME_TOKENS

logger = logging.getLogger(__name__)
import json
import datetime as dt
from decimal import Decimal, InvalidOperation
from typing import Dict, Any, List, Optional, Tuple

from jinja2 import Environment, FileSystemLoader, select_autoescape
from bs4 import BeautifulSoup
import os

# --- Funciones de Ayuda Generales ---

def _extract_field(text: str, patterns: List[str], default: str = 'No encontrado') -> str:
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            try:
                return match.group(1).strip()
            except IndexError:
                return match.group(0).strip()
    return default

def _formatear_fecha_dd_mm_yyyy(fecha_str: str) -> str:
    if not fecha_str: return fecha_str
    try:
        return dt.datetime.strptime(fecha_str.strip(), '%d %b %y').strftime('%d-%m-%Y')
    except (ValueError, TypeError):
        return fecha_str

def _fecha_a_iso(fecha_str: str) -> Optional[str]:
    if not fecha_str: return None
    try:
        return dt.datetime.strptime(fecha_str.strip(), '%d-%m-%Y').strftime('%Y-%m-%d')
    except (ValueError, TypeError):
        return None

def normalize_common_fields(raw: Dict[str, Any]) -> None:
    try:
        source = raw.get('SOURCE_SYSTEM')
        normalized = {'source_system': source}
        if source == 'SABRE':
            normalized['ticket_number'] = raw.get('numero_boleto')
            normalized['reservation_code'] = raw.get('codigo_reservacion')
            normalized['reservation_code_full'] = raw.get('codigo_reservacion')
            pasajero = raw.get('preparado_para')
            normalized['passenger_name_raw'] = pasajero
            if pasajero and '/' in pasajero:
                ap, nom = pasajero.split('/',1)
                normalized['passenger_name'] = f"{nom.strip()} {ap.strip()}".strip()
            else:
                normalized['passenger_name'] = pasajero
            normalized['airline_name'] = raw.get('aerolinea_emisora')
            normalized['issuing_agent'] = raw.get('agente_emisor')
            normalized['issuing_date_iso'] = raw.get('fecha_emision_iso')
            if raw.get('vuelos'):
                segments = []
                for idx, v in enumerate(raw.get('vuelos', []), start=1):
                    seg = {
                        'segment_index': idx,
                        'source_system': 'SABRE',
                        'flight_number': v.get('numero_vuelo'),
                        'marketing_airline': v.get('aerolinea'),
                        'origin': (v.get('origen') or {}).get('ciudad'),
                        'destination': (v.get('destino') or {}).get('ciudad'),
                        'departure_date_iso': v.get('fecha_salida_iso'),
                        'departure_time': v.get('hora_salida'),
                        'arrival_date_iso': None, 
                        'arrival_time': v.get('hora_llegada'),
                    }
                    segments.append(seg)
                normalized['segments'] = segments
        raw['normalized'] = normalized
    except Exception as e:
        logger.exception("Fallo al generar bloque normalized: %s", e)
        return

# --- Lógica de Parseo Específica para SABRE (Versión Definitiva) ---

def _parsear_itinerario_sabre_final(itinerario_texto: str) -> List[Dict[str, Any]]:
    vuelos = []
    if not itinerario_texto: return vuelos

    bloques = re.split(r'(?=\d{2}\s+\w{3}\s+\d{2})', itinerario_texto)
    
    for bloque in bloques:
        bloque = bloque.strip()
        if not bloque: continue

        flight_match = re.search(r'\b([A-Z0-9]{2}\s*\d{2,4})\b', bloque)
        if not flight_match: continue

        vuelo = {'numero_vuelo': flight_match.group(1).replace(' ', '')}
        
        all_dates = re.findall(r'(\d{2}\s+\w{3}\s+\d{2})', bloque)
        if all_dates:
            vuelo['fecha_salida'] = all_dates[0]
            vuelo['fecha_llegada'] = all_dates[1] if len(all_dates) > 1 else all_dates[0]

        vuelo['aerolinea'] = _extract_field(bloque, [r'\d{2}\s+\w{3}\s+\d{2}\s+(.+?)(?=\s+(?:SALIDA|DEPARTURE))'])
        
        origen_str = _extract_field(bloque, [r'(?:SALIDA|DEPARTURE)\s*([^\n]+?)\s*(?:LLEGADA|ARRIVAL)'])
        destino_str = _extract_field(bloque, [r'(?:LLEGADA|ARRIVAL)\s*([^\n]+)'])

        vuelo['origen'] = {"ciudad": origen_str, "pais": ""}
        vuelo['destino'] = {"ciudad": destino_str, "pais": ""}

        horas = re.findall(r'(\d{2}:\d{2})', bloque)
        if len(horas) >= 2:
            vuelo['hora_salida'] = horas[0]
            vuelo['hora_llegada'] = horas[1]

        vuelo['terminal_salida'] = _extract_field(bloque, [r'TERMINAL\s*:\s*(\S+)'])
        vuelo['terminal_llegada'] = _extract_field(bloque, [r'TERMINAL\s*:\s*(\S+)\s*LLEGADA'])
        vuelo['codigo_reservacion_local'] = _extract_field(bloque, [r'AEROLÍNEA\s*:\s*([A-Z0-9]{6})'])
        vuelo['cabina'] = _extract_field(bloque, [r'CABINA\s*:\s*(\w+)'])
        vuelo['equipaje'] = _extract_field(bloque, [r'EQUIPAJE PERMITIDO\s*:\s*(\S+)'])

        vuelos.append(vuelo)
            
    return vuelos

def _parse_sabre_ticket(plain_text: str) -> Dict[str, Any]:
    raw_data = {'SOURCE_SYSTEM': 'SABRE', 'errores': []}

    header_block = re.search(r'(.*?)(?:Itinerary Details|Información De Vuelo)', plain_text, re.DOTALL)
    itinerary_block = re.search(r'(?:Itinerary Details|Información De Vuelo)(.*?)(?=Aviso:|CONDICIONES DEL CONTRATO|Please contact)', plain_text, re.DOTALL)
    
    header_text = header_block.group(1) if header_block else plain_text
    itinerary_text = itinerary_block.group(1) if itinerary_block else ''

    # Extracción de datos crudos
    raw_data['preparado_para'] = _extract_field(header_text, [r'(?:Preparado para|Prepared For)\s*([A-ZÁÉÍÓÚ/ ]+)'])
    raw_data['documento_identidad'] = _extract_field(header_text, [r'\[([A-Z0-9]+)\]'])
    raw_data['codigo_reservacion'] = _extract_field(header_text, [r'(?:CÓDIGO DE RESERVACIÓN|Reservation Code)\s*([A-Z0-9]{6})'])
    raw_data['numero_cliente'] = _extract_field(header_text, [r'(?:NÚMERO DE CLIENTE|Customer Number)\s*([A-Z0-9]+)'])

    pattern_columnas_1 = re.compile(r"FECHA DE EMISIÓN\s+NÚMERO DE BOLETO\s+AEROLÍNEA EMISORA\s+([\d\w\s]+?)\s+(\d{13})\s+([^\n]+)", re.I)
    match_columnas_1 = pattern_columnas_1.search(header_text)
    if match_columnas_1:
        raw_data['fecha_emision'] = match_columnas_1.group(1).strip()
        raw_data['numero_boleto'] = match_columnas_1.group(2).strip()
        raw_data['aerolinea_emisora'] = match_columnas_1.group(3).strip()
    else:  
        raw_data['fecha_emision'] = _extract_field(header_text, [r'(?:Issue Date|Fecha de Emision)\s+([^\n]+)'])
        raw_data['numero_boleto'] = _extract_field(header_text, [r'(?:Ticket Number|Numero de Boleto)\s+(\d{13})'])
        raw_data['aerolinea_emisora'] = _extract_field(header_text, [r'(?:Issuing Airline|Aerolinea Emisora)\s+([^\n]+)'])

    pattern_columnas_2 = re.compile(r"AGENTE EMISOR\s+UBICACIÓN DEL AGENTE EMISOR\s+NÚMERO IATA\s+([^\n]+)\s+([^\n]+)\s+(\d+)", re.I)
    match_columnas_2 = pattern_columnas_2.search(header_text)
    if match_columnas_2:
        raw_data['agente_emisor'] = match_columnas_2.group(1).strip()
        raw_data['numero_iata'] = match_columnas_2.group(3).strip()

    raw_data['vuelos'] = _parsear_itinerario_sabre_final(itinerary_text)

    # Formateo de fechas
    raw_data['fecha_emision_fmt'] = _formatear_fecha_dd_mm_yyyy(raw_data.get('fecha_emision', ''))
    raw_data['fecha_emision_iso'] = _fecha_a_iso(raw_data.get('fecha_emision_fmt'))

    vuelos_fmt = []
    for v in raw_data.get('vuelos', []):
        v['fecha_salida_iso'] = _fecha_a_iso(_formatear_fecha_dd_mm_yyyy(v.get('fecha_salida', '')))
        v['fecha_llegada_iso'] = _fecha_a_iso(_formatear_fecha_dd_mm_yyyy(v.get('fecha_llegada', '')))
        vuelos_fmt.append(v)
    raw_data['vuelos'] = vuelos_fmt

    # Estructuración de datos para la plantilla
    data_for_template = {
        'pasajero': {
            'nombre_completo': raw_data.get('preparado_para', 'No encontrado'),
            'documento_identidad': raw_data.get('documento_identidad', 'No encontrado')
        },
        'reserva': {
            'codigo_reservacion': raw_data.get('codigo_reservacion', 'No encontrado'),
            'numero_boleto': raw_data.get('numero_boleto', 'No encontrado'),
            'fecha_emision': raw_data.get('fecha_emision_fmt', 'No encontrado'),
            'fecha_emision_iso': raw_data.get('fecha_emision_iso', 'No encontrado'),
            'aerolinea_emisora': raw_data.get('aerolinea_emisora', 'No encontrado'),
            'agente_emisor': {
                'nombre': raw_data.get('agente_emisor', 'No encontrado'),
                'numero_iata': raw_data.get('numero_iata', 'No encontrado')
            }
        },
        'itinerario': {
            'vuelos': raw_data.get('vuelos', [])
        },
        'raw_data': raw_data,
        'SOURCE_SYSTEM': 'SABRE'
    }

    normalize_common_fields(raw_data)
    data_for_template['normalized'] = raw_data['normalized']

    return data_for_template


# --- PUNTO DE ENTRADA PRINCIPAL ---

def extract_data_from_text(plain_text: str, html_text: str = "", pdf_path: Optional[str] = None) -> Dict[str, Any]:
    plain_text_upper = plain_text.upper()
    found_sabre = any([
        ('ITINERARY DETAILS' in plain_text_upper or 'INFORMACIÓN DE VUELO' in plain_text_upper),
        ('PREPARED FOR' in plain_text_upper or 'PREPARADO PARA' in plain_text_upper) and ('RESERVATION CODE' in plain_text_upper or 'CÓDIGO DE RESERVACIÓN' in plain_text_upper),
        ('ETICKET RECEIPT' in plain_text_upper or 'RECIBO DE BOLETO ELECTRÓNICO' in plain_text_upper) and ('RESERVATION CODE' in plain_text_upper or 'CÓDIGO DE RESERVACIÓN' in plain_text_upper),
    ])
    if found_sabre:
        logger.info("Detectado GDS: SABRE (parser sabre activado)")
        return _parse_sabre_ticket(plain_text)
    
    logger.warning("No se pudo determinar el GDS del boleto; retornando datos vacíos.")
    unknown = {"error": "GDS no reconocido", "SOURCE_SYSTEM": None}
    normalize_common_fields(unknown)
    return unknown

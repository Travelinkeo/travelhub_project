# Archivo: core/ticket_parser.py

import re
import logging
from .identification_utils import normalize_codigo_identificacion, extract_codigo_identificacion_anywhere
from .utils import LOCATION_TOKENS, STOP_NAME_TOKENS
from core.parsers.sabre_parser import SabreParser

logger = logging.getLogger(__name__)
import datetime as dt
from decimal import Decimal, InvalidOperation
from typing import Dict, Any, List, Optional, Tuple

from jinja2 import Environment, FileSystemLoader, select_autoescape
from bs4 import BeautifulSoup
import os

# --- Funciones de Ayuda Generales (Importadas desde parsing_utils) ---
from .parsing_utils import (
    _clean_value,
    _parse_currency_amount,
    _extract_field,
    _extract_field_single_line,
    _formatear_fecha_dd_mm_yyyy
)
from .airline_utils import normalize_airline_name, extract_airline_code_from_flight

# --- Lógica de Parseo Específica para KIU (Restaurada y Completa) ---

def _extract_block(texto: str, start_patterns: list, end_patterns: list, default='No encontrado') -> str:
    start_regex = r'(?:' + '|'.join(start_patterns) + r')'
    end_regex = r'(?:' + '|'.join(end_patterns) + r')'
    pattern_str = r'(?is)' + start_regex + r'(.*?)' + r'(?=\s*' + end_regex + r')'
    match = re.search(pattern_str, texto)
    return match.group(1).strip() if match and match.group(1) else default

def _get_numero_boleto(texto: str) -> str:
    patterns = [
        r"TICKET N[BR]O\s*[:\s]*([0-9-]{8,})",
        r"TICKET'?S? NUMBER'?S?\s*[:\s]*([0-9-]{8,})",
        r"TICKET NUMBER/NRO DE BOLETO\s*[:\s]*([0-9-]{8,})"
    ]
    return _extract_field_single_line(texto, patterns)

def _get_fecha_emision(texto: str) -> str:
    return _extract_field_single_line(texto, [
        r'ISSUE DATE/FECHA DE EMISION\s*[:\s]*([0-9]{1,2}\s+[A-Z]{3}\s+[0-9]{4}\s+[0-9]{2}:[0-9]{2})',
        r'ISSUE DATE\s*[:\s]*([0-9]{1,2}\s+[A-Z]{3}\s+[0-9]{4}\s+[0-9]{2}:[0-9]{2})'
    ])

def _get_agente_emisor(texto: str) -> str:
    return _extract_field_single_line(texto, [
        r'ISSUE AGENT/AGENTE EMISOR\s*[:\s]*([A-Z0-9]+)',
        r'ISSUE AGENT\s*[:\s]*([A-Z0-9]+)'
    ])

def _get_nombre_completo_pasajero(texto: str) -> str:
    raw = _extract_field_single_line(texto, [
        r'NAME/NOMBRE\s*[:\s]*([A-ZÁÉÍÓÚÑ/ (),.-]{3,})',
        r'NAME\s*[:\s]*([A-ZÁÉÍÓÚÑ/ (),.-]{3,})'
    ])
    if raw == 'No encontrado':
        return raw

    upper_raw = raw.upper()
    stop_tokens = STOP_NAME_TOKENS
    cut_positions = []
    for token in stop_tokens:
        idx = upper_raw.find(token)
        if idx != -1 and idx > 5:
            cut_positions.append(idx)

    par_idx = raw.find('(')
    if par_idx != -1 and par_idx > 4:
        cut_positions.append(par_idx)

    if cut_positions:
        raw = raw[:min(cut_positions)].rstrip()

    raw = re.sub(r'[^A-ZÁÉÍÓÚÑ/ ]+', ' ', raw.upper())
    raw = re.sub(r'\s{2,}', ' ', raw).strip()

    if '/' not in raw:
        return raw

    apellidos, nombres = raw.split('/', 1)
    nombres = nombres.strip()

    LOCATION_TOKENS_SET = {t.upper() for t in LOCATION_TOKENS}
    nombres = re.sub(r'(?:CIUDAD DE [A-ZÁÉÍÓÚÑ]{2,}(?:\s+[A-ZÁÉÍÓÚÑ]{2,})*)$', '', nombres).strip()

    tokens = nombres.split()
    if len(tokens) > 1:
        for i in range(1, len(tokens)):
            tail = tokens[i:]
            if tail and all(t in LOCATION_TOKENS_SET for t in tail):
                tokens = tokens[:i]
                break
        else:
            if tokens[-1] in LOCATION_TOKENS_SET:
                tokens = tokens[:-1]
    nombres_limpios = ' '.join(tokens)

    nombres_limpios = re.sub(r'\s{2,}', ' ', nombres_limpios).strip()

    return f"{apellidos.strip()}/{nombres_limpios}"

def _get_solo_nombre_pasajero(nombre_completo: str) -> str:
    if '/' in nombre_completo:
        nombre_bruto = nombre_completo.split('/')[1]
        return re.sub(r'\s*(MR|MS|MRS|CHD|INF)\s*$', '', nombre_bruto, flags=re.IGNORECASE).strip()
    return nombre_completo

def _get_codigo_identificacion(texto: str) -> str:
    codigo = normalize_codigo_identificacion(texto)
    if not codigo or codigo == 'No encontrado':
        codigo = extract_codigo_identificacion_anywhere(texto)
    return codigo

def _get_solo_codigo_reserva(texto: str) -> str:
    pattern = r"C1\s*/\s*([A-Z0-9]{6})"
    match = re.search(pattern, texto, re.IGNORECASE)
    if match and match.group(1):
        return match.group(1).strip()
    booking_ref_text = _extract_field(texto, [r'BOOKING REF\./CODIGO DE RESERVA\s*[:\s]*(.+)', r'BOOKING REF\.?\s*[:\s]*(.+)'])
    if booking_ref_text != 'No encontrado':
        match_pnr = re.search(r'\b([A-Z0-9]{6})\b', booking_ref_text)
        if match_pnr:
            return match_pnr.group(1)
    return 'No encontrado'

def _get_codigo_reserva_completo(solo_codigo: str) -> str:
    if solo_codigo and solo_codigo != 'No encontrado':
        if 'C1/' in solo_codigo.upper():
            return solo_codigo
        return f"C1/{solo_codigo}"
    return 'No encontrado'

def _extraer_itinerario_kiu(plain_text: str, html_text: str = "") -> str:
    # Intento prioritario con HTML si está disponible
    if html_text:
        try:
            soup = BeautifulSoup(html_text, 'html.parser')
            pre_tags = soup.find_all('pre')
            itinerary_content = []
            capturing = False
            
            start_keywords = ['FROM/TO', 'DESDE/HACIA']
            end_keywords = ['ENDORSEMENTS', 'CONDICIONES', 'FARE CALC', 'TOUR CODE', 'PAYMENT', 'TOTAL', 'TAX/IMPUESTOS']
            
            for tag in pre_tags:
                text_content = tag.get_text()
                # Busca el inicio del bloque de itinerario
                if any(keyword in text_content.upper() for keyword in start_keywords):
                    lines = text_content.splitlines()
                    for line in lines:
                        stripped_line = line.strip()
                        upper_line = stripped_line.upper()
                        
                        if not capturing and any(keyword in upper_line for keyword in start_keywords) and ('FLIGHT' in upper_line or 'VUELO' in upper_line):
                            capturing = True
                            # No añadir la línea de cabecera, sino lo que sigue
                            continue
                        
                        if capturing:
                            # Si se encuentra una palabra clave de fin, se detiene la captura
                            if any(keyword in upper_line for keyword in end_keywords):
                                capturing = False
                                break
                            if stripped_line:
                                itinerary_content.append(stripped_line)
                    
                    # Si se capturó algo, se detiene la búsqueda en más tags <pre>
                    if itinerary_content:
                        break
            
            if itinerary_content:
                logger.debug("Itinerario extraído exitosamente desde HTML.")
                return '\n'.join(itinerary_content)

        except Exception as e:
            logger.exception("Error durante la extracción HTML; intentando fallback a texto plano.")

    # Fallback a texto plano si HTML falla o no está disponible
    logger.warning("No se encontró itinerario HTML válido o no fue provisto; usando método de texto plano.")
    
    lines = plain_text.splitlines()
    itinerary_content = []
    capturing = False

    start_pattern = r'(FROM/TO|DESDE/HACIA)[\s/]+(FLIGHT|VUELO)'
    end_keywords = ['ENDORSEMENTS', 'CONDICIONES', 'FARE CALC', 'TOUR CODE', 'PAYMENT', 'TOTAL', 'TAX/IMPUESTOS', 'FRANQUICIA DE EQUIPAJE', 'CONDICIONES DE CONTRATO']

    for line in lines:
        stripped_line = line.strip()
        upper_line = stripped_line.upper()

        if not capturing and re.search(start_pattern, upper_line):
            capturing = True
            continue

        if capturing:
            if any(keyword in upper_line for keyword in end_keywords):
                break
            
            if stripped_line and not re.fullmatch(r'[-_\s]+', stripped_line):
                itinerary_content.append(stripped_line)

    if itinerary_content:
        # Limpieza final: a veces la segunda línea del cabecero se cuela
        if 'VUELO' in itinerary_content[0] and 'FECHA' in itinerary_content[0]:
            itinerary_content.pop(0)
        
        # Limpiar cada línea del itinerario
        cleaned_lines = []
        for line in itinerary_content:
            # Eliminar "AGENTE" y todo lo que viene después en cada línea
            line = re.sub(r'\s+AGENTE.*$', '', line, flags=re.IGNORECASE)
            if line.strip():
                cleaned_lines.append(line)
        
        logger.debug("Itinerario extraído exitosamente desde texto plano.")
        return '\n'.join(cleaned_lines)

    return "No se pudo procesar el itinerario."

def _get_tarifa(texto: str) -> str:
    return _extract_field_single_line(texto, [
        r'AIR FARE/TARIFA\s*[:\s]*([A-Z]{3}\s*[0-9,.]+)',
        r'AIR FARE\s*[:\s]*([A-Z]{3}\s*[0-9,.]+)'
    ])

def _get_impuestos(texto: str) -> str:
    start_patterns = [r'(?:TAX/IMPUESTOS|TAX)\s*:']
    end_patterns = [r'TOTAL']
    bloque_impuestos = _extract_block(texto, start_patterns, end_patterns, default="No encontrado")
    if bloque_impuestos != "No encontrado":
        lines = bloque_impuestos.strip().splitlines()
        cleaned_lines = [re.sub(r'(USD|VES)', '', line).strip() for line in lines if line.strip()]
        return ' '.join(cleaned_lines)
    return "No encontrado"

def _get_total(texto: str) -> str:
    return _extract_field_single_line(texto, [r'TOTAL\s*[:\s]*([A-Z]{3}\s*[0-9,.]+)'])

def _get_nombre_aerolinea(texto: str) -> str:
    raw = _extract_field_single_line(texto, [
        r'ISSUING AIRLINE/LINEA AEREA EMISORA\s*[:\s]*([A-Z0-9 ,.&-]{3,})',
        r'ISSUING AIRLINE\s*[:\s]*([A-Z0-9 ,.&-]{3,})'
    ])
    if raw == 'No encontrado':
        return raw
    
    # Eliminar "AGENTE" y todo lo que viene después (PRIMERO)
    raw = re.sub(r'\s+AGENTE.*$', '', raw, flags=re.IGNORECASE)
    
    # Limpiar sufijos de agente emisor (ej: /AE1, /ARP, /AR)
    raw = re.sub(r'/[A-Z0-9]{2,3}\s*$', '', raw)
    
    stop_tokens = [
        ' ADDRESS', ' ISSUE', ' BOOKING REF', ' NAME/', ' FOID', ' TICKET', ' AIR FARE', ' TAX', ' TOTAL',
        ' DESDE/HACIA', ' FROM/TO', ' C1/'
    ]
    upper_raw = raw.upper()
    cut_positions: List[int] = []
    for token in stop_tokens:
        idx = upper_raw.find(token)
        if idx > 5:
            cut_positions.append(idx)
    par_idx = raw.find('(')
    if par_idx != -1 and par_idx > 4:
        cut_positions.append(par_idx)
    if cut_positions:
        raw = raw[:min(cut_positions)].rstrip()
    raw = re.sub(r'\s{2,}', ' ', raw)
    raw = re.sub(r',\s*,+', ', ', raw)
    tail_tokens = [' ISSUE', ' ADDRESS', ' TICKET', ' AIR FARE', ' TAX', ' TOTAL']
    for tt in tail_tokens:
        pos = raw.upper().find(tt)
        if pos != -1 and pos > 10:
            raw = raw[:pos].rstrip(', ').strip()
            break
    return raw.rstrip(', ')

def _get_direccion_aerolinea(texto: str) -> str:
    return _extract_field_single_line(texto, [
        r'ADDRESS/DIRECCION\s*[:\s]*([A-Z0-9 .,/+-]{5,})',
        r'ADDRESS\s*[:\s]*([A-Z0-9 .,/+-]{5,})'
    ])

def _parse_kiu_ticket(plain_text: str, html_text: str) -> Dict[str, Any]:
    logger.info("--- INICIO DE PARSEO KIU ---")
    nombre_completo = _get_nombre_completo_pasajero(plain_text)
    solo_codigo = _get_solo_codigo_reserva(plain_text)
    nombre_aerolinea_raw = _get_nombre_aerolinea(plain_text)
    
    # Intentar extraer código de aerolínea del itinerario para normalizar el nombre
    itinerario = _extraer_itinerario_kiu(plain_text, html_text)
    primer_vuelo = None
    if itinerario and itinerario != "No se pudo procesar el itinerario.":
        # Buscar el primer número de vuelo en el itinerario
        import re
        vuelo_match = re.search(r'\b([A-Z]{2}\d+)\b', itinerario)
        if vuelo_match:
            primer_vuelo = vuelo_match.group(1)
    
    data = {
        'SOURCE_SYSTEM': 'KIU',
        'NUMERO_DE_BOLETO': _get_numero_boleto(plain_text),
        'FECHA_DE_EMISION': _get_fecha_emision(plain_text),
        'AGENTE_EMISOR': _get_agente_emisor(plain_text),
        'NOMBRE_DEL_PASAJERO': nombre_completo,
        'SOLO_NOMBRE_PASAJERO': _get_solo_nombre_pasajero(nombre_completo),
        'CODIGO_IDENTIFICACION': _get_codigo_identificacion(plain_text),
        'CODIGO_RESERVA': _get_codigo_reserva_completo(solo_codigo),
        'SOLO_CODIGO_RESERVA': solo_codigo,
        'NOMBRE_AEROLINEA': normalize_airline_name(nombre_aerolinea_raw, primer_vuelo),
        'DIRECCION_AEROLINEA': _get_direccion_aerolinea(plain_text),
        'TARIFA': _get_tarifa(plain_text),
        'IMPUESTOS': _get_impuestos(plain_text),
        'TOTAL': _get_total(plain_text),
        'ItinerarioFinalLimpio': itinerario,
    }
    tarifa_moneda, tarifa_importe = _parse_currency_amount(data['TARIFA'])
    total_moneda, total_importe = _parse_currency_amount(data['TOTAL'])
    data['TARIFA_MONEDA'] = tarifa_moneda
    data['TARIFA_IMPORTE'] = str(tarifa_importe) if tarifa_importe is not None else None
    data['TOTAL_MONEDA'] = total_moneda
    data['TOTAL_IMPORTE'] = str(total_importe) if total_importe is not None else None
    logger.info("Datos KIU extraídos y normalizados correctamente.")
    return data

# --- Lógica de Parseo para Amadeus y Travelport (Placeholders) ---

def _parse_amadeus_ticket(plain_text: str) -> Dict[str, Any]:
    from core.parsers.amadeus_parser import AmadeusParser
    parser = AmadeusParser()
    result = parser.parse(plain_text)
    return result.to_dict()

def _parse_travelport_ticket(plain_text: str) -> Dict[str, Any]:
    return {"SOURCE_SYSTEM": "TRAVELPORT", "error": "Parser para Travelport no implementado."}

# --- PUNTO DE ENTRADA PRINCIPAL ---

def extract_data_from_text(plain_text: str, html_text: str = "", pdf_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Detecta el GDS del boleto y llama al parser correspondiente.
    """
    plain_text_upper = plain_text.upper()
    logger.info("Iniciando detección de GDS...")

    # Heurística para Sabre (PRIORIDAD ALTA - muy específica)
    if ('ETICKET RECEIPT' in plain_text_upper or 'E-TICKET RECEIPT' in plain_text_upper) and \
       ('RESERVATION CODE' in plain_text_upper or 'RECORD LOCATOR' in plain_text_upper):
        logger.info("GDS detectado: SABRE. Procesando...")
        parser = SabreParser()
        result = parser.parse(plain_text)
        return result.to_dict()

    # Heurística para TK Connect (Turkish Airlines) - MUY ESPECÍFICA
    if ('IDENTIFICACIÓN DEL PEDIDO' in plain_text_upper and 'TURKISH AIRLINES' in plain_text_upper) or \
       ('GRUPO SOPORTE GLOBAL' in plain_text_upper and 'TURKISH' in plain_text_upper):
        logger.info("GDS detectado: TK_CONNECT. Procesando...")
        from core.parsers.tk_connect_parser import TKConnectParser
        parser = TKConnectParser()
        result = parser.parse(plain_text)
        return result.to_dict()
    
    # Heurística para COPA SPRK
    if ('COPA AIRLINES' in plain_text_upper and 'LOCALIZADOR DE RESERVA' in plain_text_upper) or 'SPRK' in plain_text_upper:
        logger.info("Sistema detectado: COPA_SPRK. Procesando...")
        from core.parsers.copa_parser import CopaParser
        parser = CopaParser()
        result = parser.parse(plain_text)
        return result.to_dict()
    
    # Heurística para WINGO
    if 'WINGO' in plain_text_upper or 'WINGO.COM' in plain_text_upper:
        logger.info("Sistema detectado: WINGO. Procesando...")
        from core.parsers.wingo_parser import WingoParser
        parser = WingoParser()
        result = parser.parse(plain_text)
        return result.to_dict()
    
    # Heurística para AMADEUS
    if 'ELECTRONIC TICKET RECEIPT' in plain_text_upper and 'BOOKING REF:' in plain_text_upper:
        logger.info("GDS detectado: AMADEUS. Procesando...")
        return _parse_amadeus_ticket(plain_text)
    
    # Heurística para KIU
    if 'KIUSYS.COM' in plain_text_upper or 'PASSENGER ITINERARY RECEIPT' in plain_text_upper:
        logger.info("GDS detectado: KIU. Procesando...")
        return _parse_kiu_ticket(plain_text, html_text)

    # Fallback: Si no se detecta un GDS claro, intentar con Sabre como último recurso.
    logger.warning("No se pudo determinar el GDS del boleto; intentando con Sabre como fallback.")
    try:
        parser = SabreParser()
        sabre_result = parser.parse(plain_text)
        if sabre_result and not hasattr(sabre_result, 'error'):
            logger.info("Parseo con fallback de Sabre tuvo éxito.")
            return sabre_result.to_dict()
    except Exception as e:
        logger.error(f"Fallback de Sabre falló: {e}")

    logger.error("Fallo final del parseo. No se pudo procesar el boleto con ningún parser disponible.")
    return {"error": "No se pudo reconocer el GDS del boleto y el intento de fallback falló."}

# --- GENERACIÓN DE PDF ---

def generate_ticket(data: Dict[str, Any]) -> Tuple[bytes, str]:
    """Genera un PDF a partir de los datos parseados, seleccionando la plantilla correcta."""
    source_system = data.get('SOURCE_SYSTEM', 'KIU')
    
    # Define el directorio base de las plantillas de tickets
    base_dir = os.path.dirname(os.path.abspath(__file__))
    template_dir = os.path.join(base_dir, 'templates', 'core', 'tickets')
    env = Environment(loader=FileSystemLoader(template_dir), autoescape=select_autoescape(['html', 'xml']))

    if source_system == 'AMADEUS':
        template_name = "ticket_template_amadeus.html"
        pasajero_data = data.get('pasajero', {})
        agencia_data = data.get('agencia', {})
        vuelos_data = data.get('vuelos', [])
        
        nombre_completo = pasajero_data.get('nombre_completo', '')
        solo_nombre = nombre_completo.split('/')[-1].strip() if '/' in nombre_completo else nombre_completo
        
        context = {
            'solo_nombre_pasajero': solo_nombre,
            'nombre_del_pasajero': nombre_completo,
            'codigo_identificacion': pasajero_data.get('tipo', 'ADT'),
            'solo_codigo_reserva': data.get('pnr', ''),
            'numero_de_boleto': data.get('numero_boleto', ''),
            'fecha_emision': data.get('fecha_emision', ''),
            'agente_emisor': agencia_data.get('iata', ''),
            'nombre_aerolinea': vuelos_data[0].get('aerolinea', 'N/A') if vuelos_data else 'N/A',
            'direccion_aerolinea': agencia_data.get('direccion', ''),
            'vuelos': [{
                'fecha_salida': v.get('fecha_salida', ''),
                'aerolinea': v.get('aerolinea', ''),
                'numero_vuelo': v.get('numero_vuelo', ''),
                'origen_ciudad': v.get('origen', ''),
                'destino_ciudad': v.get('destino', ''),
                'hora_salida': v.get('hora_salida', ''),
                'hora_llegada': v.get('hora_llegada', ''),
                'clase': v.get('clase', ''),
                'equipaje': v.get('equipaje', ''),
                'asiento': v.get('asiento', ''),
                'terminal_salida': '',
                'terminal_llegada': '',
            } for v in vuelos_data]
        }
    elif source_system == 'COPA_SPRK':
        template_name = "ticket_template_copa_sprk.html"
        context = {
            'pasajero': {
                'nombre_completo': data.get('pasajero', {}).get('nombre_completo', 'N/A'),
                'documento_identidad': data.get('pasajero', {}).get('documento', 'N/A')
            },
            'reserva': {
                'codigo_reservacion': data.get('pnr', 'N/A'),
                'numero_boleto': data.get('numero_boleto', 'N/A'),
                'fecha_emision': data.get('fecha_creacion', 'N/A'),
                'aerolinea_emisora': 'Copa Airlines',
                'agente_emisor': {'numero_iata': 'N/A'}
            },
            'itinerario': {
                'vuelos': [{
                    'fecha_salida': v.get('fecha_salida', 'N/A'),
                    'aerolinea': 'Copa Airlines',
                    'numero_vuelo': v.get('numero_vuelo', 'N/A'),
                    'origen': {'ciudad': v.get('origen', 'N/A')},
                    'hora_salida': v.get('hora_salida', 'N/A'),
                    'destino': {'ciudad': v.get('destino', 'N/A')},
                    'hora_llegada': v.get('hora_llegada', 'N/A'),
                    'cabina': v.get('cabina', 'N/A')
                } for v in data.get('vuelos', [])]
            }
        }
    elif source_system == 'WINGO':
        template_name = "ticket_template_wingo.html"
        context = {
            'pasajero': {
                'nombre_completo': data.get('pasajero', {}).get('nombre_completo', 'N/A'),
                'documento_identidad': 'N/A'
            },
            'reserva': {
                'codigo_reservacion': data.get('pnr', 'N/A'),
                'fecha_emision': data.get('fecha_creacion', 'N/A'),
                'aerolinea_emisora': 'Wingo'
            },
            'itinerario': {
                'vuelos': [{
                    'fecha_salida': v.get('fecha_salida', 'N/A'),
                    'aerolinea': 'Wingo',
                    'numero_vuelo': v.get('numero_vuelo', 'N/A'),
                    'origen': {'ciudad': v.get('origen', 'N/A')},
                    'hora_salida': v.get('hora_salida', 'N/A'),
                    'destino': {'ciudad': v.get('destino', 'N/A')},
                    'hora_llegada': v.get('hora_llegada', 'N/A'),
                    'cabina': v.get('cabina', 'N/A')
                } for v in data.get('vuelos', [])]
            }
        }
    elif source_system == 'TK_CONNECT':
        template_name = "ticket_template_tk_connect.html"
        
        # Contexto para TK Connect
        context = {
            'pasajero': {
                'nombre_completo': data.get('pasajero', {}).get('nombre_completo', 'N/A'),
                'documento_identidad': data.get('pasajero', {}).get('telefono', 'N/A')
            },
            'reserva': {
                'codigo_reservacion': data.get('pnr', 'N/A'),
                'numero_boleto': data.get('numero_boleto', 'N/A'),
                'fecha_emision': data.get('fecha_creacion', 'N/A'),
                'aerolinea_emisora': 'Turkish Airlines',
                'agente_emisor': {'numero_iata': data.get('oficina_emision', 'N/A')}
            },
            'itinerario': {
                'vuelos': [{
                    'fecha_salida': v['fecha_salida'],
                    'aerolinea': 'Turkish Airlines',
                    'numero_vuelo': v['numero_vuelo'],
                    'origen': {'ciudad': v['origen']},
                    'hora_salida': v['hora_salida'],
                    'destino': {'ciudad': v['destino']},
                    'hora_llegada': v['hora_llegada'],
                    'cabina': v['cabina']
                } for v in data.get('vuelos', [])]
            }
        }
    elif source_system.startswith('SABRE'):
        template_name = "ticket_template_sabre.html"
        
        # Adaptador para la nueva estructura de datos de Sabre (IA o Regex)
        pasajero_data = data.get('pasajero', {})
        reserva_data = data.get('reserva', {})
        itinerario_data = data.get('itinerario', {})
        agente_data = reserva_data.get('agente_emisor', {})

        # Corregido: Construir el contexto con la estructura anidada que la plantilla espera
        context = {
            'pasajero': {
                'nombre_completo': pasajero_data.get('nombre_completo', ''),
                'documento_identidad': pasajero_data.get('documento_identidad', '-')
            },
            'reserva': {
                'codigo_reservacion': reserva_data.get('codigo_reservacion', ''),
                'numero_boleto': reserva_data.get('numero_boleto', ''),
                'fecha_emision': _formatear_fecha_dd_mm_yyyy(reserva_data.get('fecha_emision_iso', '')),
                'aerolinea_emisora': reserva_data.get('aerolinea_emisora', ''),
                'agente_emisor': {
                    'nombre': agente_data.get('nombre', ''),
                    'numero_iata': agente_data.get('numero_iata', '-')
                }
            },
            'itinerario': {
                'vuelos': itinerario_data.get('vuelos', [])
            },
        }
    else: # Default para KIU
        template_name = "ticket_template_kiu.html"
        context = {
            'solo_nombre_pasajero': data.get('SOLO_NOMBRE_PASAJERO', ''),
            'solo_codigo_reserva': data.get('SOLO_CODIGO_RESERVA', ''),
            'numero_de_boleto': data.get('NUMERO_DE_BOLETO', ''),
            'nombre_del_pasajero': data.get('NOMBRE_DEL_PASAJERO', ''),
            'codigo_identificacion': data.get('CODIGO_IDENTIFICACION', ''),
            'fecha_de_emision': data.get('FECHA_DE_EMISION', ''),
            'agente_emisor': data.get('AGENTE_EMISOR', ''),
            'nombre_aerolinea': data.get('NOMBRE_AEROLINEA', ''),
            'direccion_aerolinea': data.get('DIRECCION_AEROLINEA', ''),
            'salidas': data.get('ItinerarioFinalLimpio', ''),
        }
    
    try:
        template = env.get_template(template_name)
        html_out = template.render(context)
    except Exception as e:
        logger.error(f"Error al renderizar la plantilla {template_name}: {e}")
        return b'', "error_template.pdf"

    try:
        from weasyprint import HTML
        pdf_bytes = HTML(string=html_out, base_url=base_dir).write_pdf()
    except Exception as e:
        raise RuntimeError(f"WeasyPrint no está disponible. Error: {e}")

    timestamp = dt.datetime.now().strftime("%Y%m%d%H%M%S")
    ticket_num_raw = (
        context.get('reserva', {}).get('numero_boleto') or 
        context.get('numero_de_boleto') or 
        data.get("NUMERO_DE_BOLETO", "SIN_TICKET")
    )
    ticket_num_for_file = re.sub(r'[\\/*?:",<>|]', "", _clean_value(ticket_num_raw)).replace(" ", "_") or "SIN_TICKET"
    file_name = f"Boleto_{ticket_num_for_file}_{timestamp}.pdf" 
    
    return pdf_bytes, file_name
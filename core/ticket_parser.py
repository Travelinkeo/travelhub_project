
# Archivo: core/ticket_parser.py

import re
import logging
import datetime as dt
from decimal import Decimal, InvalidOperation
from typing import Dict, Any, List, Optional, Tuple
import os
import pdfplumber
import json
from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader, select_autoescape

from .identification_utils import normalize_codigo_identificacion, extract_codigo_identificacion_anywhere
from .utils import LOCATION_TOKENS, STOP_NAME_TOKENS
from .airline_utils import normalize_airline_name
from core.parsers.sabre_parser import SabreParser
from core.parsers.web_receipt_parser import WebReceiptParser
from core.parsers.ai_universal_parser import UniversalAIParser

logger = logging.getLogger(__name__)

# --- Funciones de Ayuda Generales ---

def _normalize_and_clean_content(plain_text: str, html_text: str = None) -> str:
    """
    Ingeniería de Limpieza: Convierte HTML a texto plano limpio, 
    elimina ruidos de email (=), colapsa espacios y normaliza.
    """
    text = ""
    if html_text:
        try:
            soup = BeautifulSoup(html_text, "html.parser")
            # Eliminar elementos no textuales
            for s in soup(["script", "style", "head", "title", "meta", "[document]"]):
                s.decompose()
            text = soup.get_text(separator=' ')
        except Exception as e:
            logger.warning(f"Error BeautifulSoup: {e}")
            text = plain_text
    else:
        text = plain_text

    # 1. Eliminar "Salto de Línea Suave" (Quoted-Printable del email =)
    text = text.replace("=\r\n", "").replace("=\n", "")
    
    # 2. Reemplazar entidades HTML comunes
    text = text.replace("&nbsp;", " ").replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")
    
    # 3. Eliminar etiquetas HTML residuales
    text = re.sub(r'<[^>]+>', ' ', text)
    
    # 4. Colapsar espacios múltiples y saltos de línea excesivos
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n\s*\n', '\n', text)
    
    res = text.strip()
    return res


def _extract_field_single_line(texto: str, patterns: list, default='No encontrado') -> str:
    for pattern in patterns:
        match = re.search(pattern, texto, re.IGNORECASE)
        if match:
            try:
                val = match.group(1).strip()
            except IndexError:
                val = match.group(0).strip()
            
            # Limpieza extra de artefactos HTML
            val = re.sub(r'<[^>]+>', '', val)
            val = val.replace('&nbsp;', ' ').strip()
            val = val.rstrip('<>').strip()
            return val
    return default

def _extract_block(texto: str, start_patterns: list, end_patterns: list, default='No encontrado') -> str:
    start_regex = r'(?:' + '|'.join(start_patterns) + r')'
    end_regex = r'(?:' + '|'.join(end_patterns) + r')'
    pattern_str = r'(?is)' + start_regex + r'(.*?)' + r'(?=\s*' + end_regex + r')'
    match = re.search(pattern_str, texto)
    return match.group(1).strip() if match and match.group(1) else default

def _clean_value(val):
    if not val: return None
    return str(val).strip()

def _parse_currency_amount(text_val: str) -> Tuple[Optional[str], Optional[Decimal]]:
    if not text_val or text_val == 'No encontrado':
        return None, None
    text_val = text_val.upper().replace('USD', '').replace('VES', '').replace('$','').strip()
    try:
        amount = Decimal(text_val.replace(',', ''))
        return ('USD', amount) # Asumimos USD si no se especifica
    except InvalidOperation:
        return (None, None)

def _apply_universal_schema_filter(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    🛡️ FILTRO DE SALIDA UNIVERSAL (REGLA DE ORO)
    Asegura que el JSON final tenga exactamente las llaves solicitadas por el usuario.
    """
    if not data or "error" in data: return data
    
    # 1. Normalizar Vuelos
    vuelos_normalized = []
    vuelos_raw = data.get('vuelos') or data.get('flights') or []
    
    for v in vuelos_raw:
        loc_aerolinea = v.get("localizador_aerolinea") or v.get("airline_pnr") or v.get("pnr_aerolinea") or \
                        v.get("codigo_reservacion_local") or data.get("CODIGO_RESERVA")
        
        vuelos_normalized.append({
            "aerolinea": v.get("aerolinea") or v.get("airline") or data.get("NOMBRE_AEROLINEA") or "Aerolínea Desconocida",
            "numero_vuelo": v.get("numero_vuelo") or v.get("flight_number") or "N/A",
            "origen": v.get("origen") if isinstance(v.get("origen"), str) else (v.get("origen") or {}).get("ciudad", "ORI"),
            "fecha_salida": v.get("fecha_salida") or v.get("fecha") or "N/A",
            "hora_salida": v.get("hora_salida") or "N/A",
            "destino": v.get("destino") if isinstance(v.get("destino"), str) else (v.get("destino") or {}).get("ciudad", "DES"),
            "hora_llegada": v.get("hora_llegada") or "N/A",
            "cabina": v.get("cabina") or "Económica",
            "clase": v.get("clase") or "Y",
            "localizador_aerolinea": loc_aerolinea,
            "equipaje": v.get("equipaje") or "N/A"
        })

    # 2. Limpieza Radical de Valores (Eliminar etiquetas repetitivas)
    def clean_label(val, is_finance=False):
        if not val or val == "No encontrado": return "0.00" if is_finance else "No encontrado"
        s = str(val).strip()
        
        # Eliminar prefijos comunes conocidos
        prefixes = [
            r"/FECHA DE EMISION:", r"FECHA DE EMISION:", r"FECHA DE EMISION",
            r"NAME:", r"ASUNTO DEL CORREO:", r"PNR:", r"LOCALIZADOR:",
            r"NUMERO DE BOLETO:", r"TICKET NBR:", r"TICKET NUMBER:",
            r"USD", r"VES", r"COP", r"EUR", r"\$"
        ]
        for p in prefixes:
            s = re.sub(p, '', s, flags=re.IGNORECASE).strip()
            
        if is_finance:
            # Extraer solo el último número decimal encontrado (por si hay basura antes)
            nums = re.findall(r"(\d+\.?\d*)", s.replace(',', ''))
            if nums:
                return nums[-1]
            return "0.00"
            
        return s

    tarifa_str = clean_label(data.get("TARIFA") or data.get("fare_amount"), is_finance=True)
    total_str = clean_label(data.get("TOTAL") or data.get("total_amount"), is_finance=True)
    
    # Calcular impuestos matemáticamente si el total > tarifa
    try:
        t_val = float(total_str)
        tf_val = float(tarifa_str)
        if t_val >= tf_val:
            impuestos_str = f"{t_val - tf_val:.2f}"
        else:
            impuestos_str = clean_label(data.get("IMPUESTOS") or "0.00", is_finance=True)
    except:
        impuestos_str = "0.00"
    
    # Limpiar solo el PNR (6 chars)
    pnr = clean_label(data.get("CODIGO_RESERVA") or data.get("pnr"))
    if len(pnr) > 6:
        pnr_match = re.search(r'([A-Z0-9]{6})', pnr.upper())
        if pnr_match: pnr = pnr_match.group(1)

    solo_nombre_final = clean_label(data.get("SOLO_NOMBRE_PASAJERO") or data.get("solo_nombre_pasajero"))
    if solo_nombre_final and solo_nombre_final != "No encontrado":
        # Tomar solo la primera palabra (Primer Nombre)
        solo_nombre_final = solo_nombre_final.split()[0]
        
    aerolinea_final = clean_label(data.get("NOMBRE_AEROLINEA") or data.get("nombre_aerolinea"))
    sys_final = data.get("SOURCE_SYSTEM") or data.get("source_system", "AI_UNKNOWN")
    if 'COPA' in sys_final and (not aerolinea_final or aerolinea_final == "No encontrado" or aerolinea_final == "A AIRLINES"):
        aerolinea_final = "COPA AIRLINES"

    res = {
        "NOMBRE_DEL_PASAJERO": clean_label(data.get("NOMBRE_DEL_PASAJERO") or data.get("passenger_name") or data.get("nombre_pasajero")),
        "CODIGO_IDENTIFICACION": clean_label(data.get("CODIGO_IDENTIFICACION") or data.get("FOID") or data.get("codigo_identificacion")),
        "SOLO_NOMBRE_PASAJERO": solo_nombre_final,
        "NUMERO_DE_BOLETO": clean_label(data.get("NUMERO_DE_BOLETO") or data.get("ticket_number") or data.get("numero_boleto")),
        "FECHA_DE_EMISION": clean_label(data.get("FECHA_DE_EMISION") or data.get("fecha_emision")),
        "AGENTE_EMISOR": clean_label(data.get("AGENTE_EMISOR") or data.get("agente_emisor")),
        "CODIGO_RESERVA": pnr,
        "SOLO_CODIGO_RESERVA": pnr,
        "NOMBRE_AEROLINEA": aerolinea_final,
        "vuelos": vuelos_normalized,
        "TARIFA": tarifa_str,
        "IMPUESTOS": impuestos_str,
        "TOTAL": total_str,
        "SOURCE_SYSTEM": sys_final,
        "es_remision": data.get("es_remision", False)
    }
    
    # Mapping duplicado para compatibilidad visual con el usuario
    for k in list(res.keys()):
        if "_" in k:
            res[k.replace("_", " ")] = res[k]

    return res

# --- Extractores Específicos (Lógica KIU / Main 4.py) ---

def _get_numero_boleto(texto: str) -> str:
    patterns = [
        r"(?:TICKET N[BR]O|TICKET NUMBER|NRO DE BOLETO|BOLETO NRO)\s*[:\s]*([\d-]+)", 
        r"(?:ETICKET|E-TICKET|BOLETO ELECTR\u00d3NICO)\s*[:\s]*([\d-]+)",
        r"308-?(\d{10})" # Especial Conviasa
    ]
    return _extract_field_single_line(texto, patterns)

def _get_fecha_emision(texto: str) -> str:
    # 🎯 PRIORIDAD 1: Labels estándar
    match = re.search(r'\b(?:ISSUE DATE|FECHA DE EMISI[ÓO]N|EMITIDO EL|EMISI[ÓO]N)\b\s*[:\s]*([^ \n\r][^\n\r/]+)', texto, re.IGNORECASE)
    if match: return match.group(1).strip()
    
    # 🥈 PRIORIDAD 2: Patrón de fecha aéreo (DDMMMYYYY) precedido por una palabra "emisi..."
    match = re.search(r'emisi[^\n]*?([0-9]{1,2}[A-Z]{3}[0-9]{2,4})', texto, re.IGNORECASE)
    if match: return match.group(1).strip()

    return _extract_field_single_line(texto, [
        r'\bISSUE DATE/FECHA DE EMISIÓN\b\s*[:\s]*([^ \n\r][^\n\r]+)',
        r'\bISSUE DATE/FECHA DE EMISION\b\s*[:\s]*([^ \n\r][^\n\r]+)',
        r'\b(?:FECHA DE EMISIÓN|ISSUE DATE)\b\s*[:\s]*([^ \n\r][^\n\r]+)',
        r'\bEMITIDO\s+EL\b\s*[:\s]*([A-Z0-9 ]+)'
    ])


def _get_agente_emisor(texto: str) -> str:
    val = _extract_field_single_line(texto, [
        r'\b(?:ISSUE AGENT|AGENTE EMISOR|AGENTE)\b\s*[:\s]*([^ \n\r/]+)', 
    ])
    if val != 'No encontrado':
        # 🛡️ Regla de Memoria: Extraer solo el número/ID, no el nombre de la agencia
        match = re.search(r'([A-Z0-9]{3,})', val)
        if match: return match.group(1)
    return val


def _get_nombre_completo_pasajero(texto: str) -> str:
    # Ingeniería de Frontera: Detenerse ante palabras clave de otros campos
    stop_keywords = r"FOID|TICKET|NBR|NRO|DATE|FECHA|EMISION|ISSUE|AGENT|AGENTE|REF|RECORD|LOCALIZADOR|PNR|ISSUING|CONTACT|PHONE|EMAIL|CORREO|DOCUMENTO|ADDRESS|DIRECCION"
    
    # 🎯 PRIORIDAD: Nombres que contienen el slash "/" (Standard aéreo)
    # Ignoramos "Hola", "Estimado", "Querido" y ruidos de marketing
    greedy_name_pattern = r"(?:NAME/NOMBRE|NAME|NOMBRE|PASAJERO)\s*[:\s]*\b(?!(?:HOLA|ESTIMADO|QUERIDO|BIENVENIDO)\b)((?:(?!\s*\b(?:" + stop_keywords + r")\b[:\s]).)+)"
    
    potential_names = re.findall(greedy_name_pattern, texto, re.IGNORECASE)
    if potential_names:
        # 1. Buscar el que tenga un slash "/"
        for cand in potential_names:
            cand = cand.strip()
            if '/' in cand and len(cand) > 5:
                # Verificar que no termine en stop_keyword pegado
                cand = re.split(r'\s+\b(?:' + stop_keywords + r')\b[:\s]', cand, flags=re.IGNORECASE)[0]
                return cand.strip()
        
        # 2. Si ninguno tiene slash, buscar el más largo que no sea ruido
        long_names = [n.strip() for n in potential_names if len(n.strip()) > 3]
        if long_names:
            # Preferir el que NO sea "Hola SEBASTIAN" (ya filtrado por lookahead, pero por si acaso)
            best_cand = max(long_names, key=len)
            best_cand = re.split(r'\s+\b(?:' + stop_keywords + r')\b[:\s]', best_cand, flags=re.IGNORECASE)[0]
            return best_cand.strip()

    # Fallback legacy mejorado
    match = re.search(r'\b([A-Z]{2,}(?:/[A-Z/ ]+)+)\b', texto)
    if match: return match.group(1).strip()
    
    # ÚLTIMA INSTANCIA: Regex original refinada
    return _extract_field_single_line(texto, [greedy_name_pattern])


def _get_solo_nombre_pasajero(nombre_completo: str) -> str:
    if not nombre_completo or nombre_completo == 'No encontrado': return ""
    
    # GDS Format: APELLIDO/NOMBRE
    if '/' in nombre_completo:
        # Extraer lo que está después del "/"
        nombre_bruto = nombre_completo.split('/')[1].strip()
        # Limpiar títulos CHD, INF, MR, etc.
        nombre_limpio = re.sub(r'\s*(MR|MS|MRS|CHD|INF|MSTR|MISS)\s*$', '', nombre_bruto, flags=re.IGNORECASE).strip()
        # Quedarse solo con el primer nombre
        return nombre_limpio.split()[0] if nombre_limpio else ""
    
    # Web Format: NOMBRE NOMBRE APELLIDO APELLIDO
    # Asumimos que la primera palabra es el nombre
    return nombre_completo.split()[0]

def _get_codigo_identificacion(texto: str) -> str:
    valor = _extract_field_single_line(texto, [
        r'\b(?:FOID/D\.IDENTIDAD|FOID|DOCUMENTO)\b\s*[:\s]*([^ \n\r]+)',
        # 🔒 [SECURITY] ID con \b y dos puntos para evitar capturar SMTP id de headers
        r'\bID\b\s*:\s*([^ \n\r]+)',
    ])
    if valor != 'No encontrado':
        if "RIF" in valor.upper():
            return valor.upper().split("RIF")[0].strip()
        return valor
    
    # Fallback legacy
    return normalize_codigo_identificacion(texto) or 'No encontrado'


def _get_solo_codigo_reserva(texto: str) -> str:
    # Prioridad: Formato KIU C1/XXXXXX
    match = re.search(r"C1\s*/\s*([A-Z0-9]{6})", texto, re.IGNORECASE)
    if match: return match.group(1).strip().upper()
    
    # B\u00fasqueda biling\u00fce
    patterns = [
        r'(?:BOOKING REF|CODIGO DE RESERVA|RECORD LOCATOR|LOCALIZADOR|PNR)\s*[:\s]*([A-Z0-9]{6})'
    ]
    return _extract_field_single_line(texto, patterns).upper()


def _get_codigo_reserva_completo(solo_codigo: str) -> str:
    if solo_codigo and solo_codigo != 'No encontrado':
        if solo_codigo.upper().startswith('C1/'): return solo_codigo.upper()
        return f"C1/{solo_codigo.upper()}"
    return 'No encontrado'


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
    # 🎯 Regla de Memoria: El total debe ser rastreable
    val = _extract_field_single_line(texto, [r'TOTAL\s*[:\s]*([A-Z]{3}\s*[0-9,.]+)'])
    return val

def _get_nombre_aerolinea(texto: str) -> str:
    patterns = [
        r'(?:ISSUING AIRLINE|LINEA AEREA EMISORA|AIRLINE|AEROLINEA)\s*[:\s]*([A-Z0-9 ,.&-]{3,})',
    ]
    raw = _extract_field_single_line(texto, patterns)
    if raw == 'No encontrado':
        return raw
    
    # Limpieza de basura residual
    raw = re.sub(r'\s+AGENTE.*$', '', raw, flags=re.IGNORECASE)
    raw = re.sub(r'/[A-Z0-9]{2,3}\s*$', '', raw)
    return raw.strip().rstrip(', ').upper()


def _get_direccion_aerolinea(texto: str) -> str:
    return _extract_field_single_line(texto, [
        # Match Address stopping before RIF, TELF or other starting labels
        r'\bADDRESS/DIRECCION\b\s*[:\s]*((?:(?!\s+\b(?:RIF|TELF|TICKET|BOLETO|NAME|NOMBRE)\b).)+)', 
        r'\bADDRESS\b\s*[:\s]*((?:(?!\s+\b(?:RIF|TELF|TICKET|BOLETO|NAME|NOMBRE)\b).)+)', 
    ])


# --- Logic Itinerario ---

def _extraer_itinerario_kiu(plain_text: str, html_text: str = "") -> str:
    if html_text:
        try:
            soup = BeautifulSoup(html_text, 'html.parser')
            pre_tags = soup.find_all('pre')
            itinerary_content = []
            capturing = False
            start_keywords = ['FROM/TO', 'DESDE/HACIA', 'ITINERARY', 'ITINERARIO', 'DESDE', 'HACIA']
            end_keywords = ['ENDORSEMENTS', 'CONDICIONES', 'FARE CALC', 'TOUR CODE', 'PAYMENT', 'TOTAL', 'TAX/IMPUESTOS']
            
            for tag in pre_tags:
                text_content = tag.get_text()
                if any(keyword in text_content.upper() for keyword in start_keywords):
                    lines = text_content.splitlines()
                    for line in lines:
                        stripped_line = line.strip()
                        upper_line = stripped_line.upper()
                        if not capturing and any(keyword in upper_line for keyword in start_keywords) and ('FLIGHT' in upper_line or 'VUELO' in upper_line):
                            capturing = True
                            continue
                        if capturing:
                            if any(keyword in upper_line for keyword in end_keywords):
                                capturing = False
                                break
                            if stripped_line:
                                # Clean potential HTML tags (e.g. <B>CARACAS</B>)
                                # 🧹 CLEANING: Remove asterisks and colapse spaces
                                clean_line = re.sub(r'<[^>]+>', '', stripped_line).replace('*', ' ').strip()
                                clean_line = re.sub(r'\s+', ' ', clean_line)
                                if clean_line:
                                    itinerary_content.append(clean_line)
                    if itinerary_content: break
            
            if itinerary_content: return '\n'.join(itinerary_content)
        except Exception: pass

    # Fallback texto plano
    lines = plain_text.splitlines()
    itinerary_content = []
    capturing = False
    start_pattern = r'(FROM/TO|DESDE/HACIA|ITINERARY|ITINERARIO|DESDE|HACIA)[\s/]+(FLIGHT|VUELO)'
    end_keywords = ['ENDORSEMENTS', 'CONDICIONES', 'FARE CALC', 'TOUR CODE', 'PAYMENT', 'TOTAL', 'TAX/IMPUESTOS', 'FRANQUICIA DE EQUIPAJE', 'CONDICIONES DE CONTRATO']

    for line in lines:
        stripped_line = line.strip()
        upper_line = stripped_line.upper()
        if not capturing and re.search(start_pattern, upper_line):
            capturing = True
            continue
        if capturing:
            if any(keyword in upper_line for keyword in end_keywords): break
            if stripped_line and not re.fullmatch(r'[-_\s]+', stripped_line):
                # Clean potential HTML tags (Safety net for fallback)
                # 🧹 CLEANING: Remove asterisks and colapse spaces
                clean_line = re.sub(r'<[^>]+>', '', stripped_line).replace('*', ' ').strip()
                clean_line = re.sub(r'\s+', ' ', clean_line)
                if clean_line:
                    itinerary_content.append(clean_line)
    
    if itinerary_content:
        if 'VUELO' in itinerary_content[0] and 'FECHA' in itinerary_content[0]:
            itinerary_content.pop(0)
        return '\n'.join([l for l in itinerary_content if l.strip()])
    return "No se pudo procesar el itinerario."

def _parse_kiu_flight_segments(itinerary_text: str) -> List[Dict[str, Any]]:
    vuelos = []
    if not itinerary_text: return vuelos

    # Regex Standards
    patterns = [
        re.compile(r'(\d{1,2}[A-Z]{3}\d{0,2})\s+([A-Z0-9]{2,3}\s*\d{1,4}[A-Z]?)\s+([A-Z]{3})\s*(\d{4})\s*-?\s*([A-Z]{3})\s*(\d{4})(.*)'),
        re.compile(r'(\d{1,2}[A-Z]{3}\d{0,2})\s+([A-Z0-9]{2,3}\s*\d{1,4}[A-Z]?)\s+([A-Z]{3})\s+(\d{4})\s+([A-Z]{3})\s+(\d{4})(.*)') 
    ]
    
    # New pattern for Avior/Travelinkeo format (e.g. BARQUISIMETO9V 071 T 18FEB 1815 1900)
    avior_pattern = re.compile(r'^([A-Z]+)(\d[A-Z]|[A-Z]\d|[A-Z]{2})\s+(\d{1,4})\s+([A-Z])\s+(\d{1,2}[A-Z]{3})\s+(\d{4})\s+(\d{4})(.*)')
    conviasa_pattern = re.compile(r'^([A-Z \.]+)\s+([A-Z0-9]{2}\s*\d{3,4})\s+([A-Z])\s+(\d{1,2}[A-Z]{3})\s+(\d{4})\s+(\d{4})(.*)')

    lines = [l.strip() for l in itinerary_text.split('\n') if l.strip()]
    i = 0
    while i < len(lines):
        line = lines[i]
        # Limpiar tags y ruido de asteriscos comunes en Conviasa/HTML
        line = re.sub(r'<[^>]+>', '', line).replace('*', ' ').strip()
        matched = False
        
        # Try Avior pattern first (more specific)
        m_avior = avior_pattern.match(line)
        if m_avior:
            origen = m_avior.group(1).strip()
            # If the city is very long, maybe the airline code is partially merged?
            # But usually it's [CITY][CODE] with 2 chars code.
            # Fix if code is 3 chars like 9V
            code = m_avior.group(2)
            
            hora_salida = m_avior.group(6)
            hora_llegada = m_avior.group(7)
            if len(hora_salida) == 4: hora_salida = f"{hora_salida[:2]}:{hora_salida[2:]}"
            if len(hora_llegada) == 4: hora_llegada = f"{hora_llegada[:2]}:{hora_llegada[2:]}"
            
            destino = "---"
            # In this format, destination is often on the NEXT line
            if i + 1 < len(lines):
                next_line = re.sub(r'<[^>]+>', '', lines[i+1]).strip()
                if not any(p.search(next_line) for p in patterns) and \
                   not avior_pattern.match(next_line) and \
                   not conviasa_pattern.match(next_line) and \
                   len(next_line) < 30:
                    destino = next_line
            
            vuelos.append({
                'fecha': m_avior.group(5),
                'aerolinea': code,
                'numero_vuelo': f"{code}{m_avior.group(3)}",
                'origen': origen,
                'hora_salida': hora_salida,
                'destino': destino,
                'hora_llegada': hora_llegada,
                'clase': m_avior.group(4),
                'equipaje': "23K" if "23K" in m_avior.group(8) else ("1PC" if "1PC" in m_avior.group(8) else "")
            })
            matched = True
            if destino != "---": i += 1 # Skip destination line
        
        if not matched:
            for p in patterns:
                m = p.search(line)
                if m: ...
        
        if not matched:
            m = conviasa_pattern.search(line)
            if m:
                origen = m.group(1).strip()
                hora_salida = m.group(5)
                hora_llegada = m.group(6)
                if len(hora_salida) == 4: hora_salida = f"{hora_salida[:2]}:{hora_salida[2:]}"
                if len(hora_llegada) == 4: hora_llegada = f"{hora_llegada[:2]}:{hora_llegada[2:]}"
                
                destino = "---"
                if i + 1 < len(lines):
                     candidate = lines[i+1]
                     if not conviasa_pattern.search(candidate) and len(candidate) < 30:
                         destino = candidate.split("PARA MAYOR")[0].strip()
                
                vuelos.append({
                    'fecha': m.group(4),
                    'aerolinea': m.group(2).replace(" ", "")[:2],
                    'numero_vuelo': m.group(2).replace(" ", ""),
                    'origen': origen,
                    'hora_salida': hora_salida,
                    'destino': destino,
                    'hora_llegada': hora_llegada,
                    'equipaje': "23K" if "23K" in m.group(7) else "1PC"
                })
                matched = True
        
        i += 1
    return vuelos

def _parse_kiu_ticket(plain_text: str, html_text: str) -> Dict[str, Any]:
    logger.info("--- INICIO DE PARSEO KIU ---")
    nombre_completo = _get_nombre_completo_pasajero(plain_text)
    solo_codigo = _get_solo_codigo_reserva(plain_text)
    nombre_aerolinea_raw = _get_nombre_aerolinea(plain_text)
    
    itinerario = _extraer_itinerario_kiu(plain_text, html_text)
    vuelos_semanticos = []
    primer_vuelo = None

    if itinerario and itinerario != "No se pudo procesar el itinerario.":
        vuelo_match = re.search(r'\b([A-Z]{2}\d+)\b', itinerario)
        if vuelo_match: primer_vuelo = vuelo_match.group(1)
        vuelos_semanticos = _parse_kiu_flight_segments(itinerario)
    
    data = {
        'SOURCE_SYSTEM': 'KIU',
        'NUMERO_DE_BOLETO': _get_numero_boleto(plain_text),
        'FECHA_DE_EMISION': _get_fecha_emision(plain_text),
        'AGENTE_EMISOR': _get_agente_emisor(plain_text),
        'NOMBRE_DEL_PASAJERO': nombre_completo,
        'SOLO_NOMBRE_PASAJERO': _get_solo_nombre_pasajero(nombre_completo),
        'CODIGO_IDENTIFICACION': _get_codigo_identificacion(plain_text),
        # 🔑 REGLA UNIVERSAL: Capturar el PNR limpio (sin C1/)
        'CODIGO_RESERVA': solo_codigo,
        'SOLO_CODIGO_RESERVA': solo_codigo,
        'NOMBRE_AEROLINEA': normalize_airline_name(nombre_aerolinea_raw, primer_vuelo),
        'DIRECCION_AEROLINEA': _get_direccion_aerolinea(plain_text),
        'TARIFA': _get_tarifa(plain_text),
        'IMPUESTOS': _get_impuestos(plain_text),
        'TOTAL': _get_total(plain_text),
        'ItinerarioFinalLimpio': itinerario,
        'vuelos': vuelos_semanticos
    }
    
    # Normalización Financiera (Mantenemos compatibilidad con el servicio)
    _, tarifa_importe = _parse_currency_amount(data['TARIFA'])
    total_moneda, total_importe = _parse_currency_amount(data['TOTAL'])
    data['TARIFA_MONEDA'], data['TARIFA_IMPORTE'] = total_moneda, str(tarifa_importe) if tarifa_importe else None
    data['TOTAL_MONEDA'], data['TOTAL_IMPORTE'] = total_moneda, str(total_importe) if total_importe else None
    
    return data

def _parse_amadeus_ticket(plain_text: str) -> Dict[str, Any]:
    from core.parsers.amadeus_parser import AmadeusParser
    return AmadeusParser().parse(plain_text).to_dict()

def _parse_travelport_ticket(plain_text: str) -> Dict[str, Any]:
    return {"SOURCE_SYSTEM": "TRAVELPORT", "error": "Not implemented"}

# --- ROUTER ---

def extract_data_from_text(plain_text: str, html_text: str = "", pdf_path: Optional[str] = None) -> Dict[str, Any]:
                # --- CAPA DE NORMALIZACIÓN DE ALTA INTEGRIDAD ---
    clean_text = _normalize_and_clean_content(plain_text, html_text)
    plain_text_upper = clean_text.upper()
    
    logger.info(f"🔍 [Deep-Integrity] Pre-processed Text Preview: {clean_text[:150]!r}")
    
    # Inyectar texto limpio para los parsers subsiguientes
    plain_text = clean_text 

    # 🚀 MOTOR UNIVERSAL IA (PRIMERA PRIORIDAD)
    # Intentamos parsear semánticamente con Gemini 2.0 Flash
    print("[AI] Iniciando Motor Universal IA (Gemini 2.0 Flash)...")
    try:
        from core.parsers.ai_universal_parser import UniversalAIParser
        ai_parser = UniversalAIParser()
        res_ai = ai_parser.parse(plain_text)
        
        # Validar si la IA tuvo éxito y extrajo datos mandatorios (Usando llaves estandarizadas)
        if res_ai and "error" not in res_ai and res_ai.get("NOMBRE_DEL_PASAJERO"):
            print(f"[OK] Éxito con Motor IA (Sistema: {res_ai.get('SOURCE_SYSTEM')})")
            return _apply_universal_schema_filter(res_ai)
        else:
            error_msg = res_ai.get('error') if res_ai else 'Datos incompletos'
            print(f"[!] Motor IA no pudo extraer datos clave o falló: {error_msg}")
    except Exception as e:
        print(f"[ERROR] Error fatal en integración con IA: {e}")

    logger.info("🔄 Iniciando Motores de Fallback (RegEx)...")

    # 1. Web Receipt (Avior/Estelar/Rutaca) - Priority for EML/HTML
    # Critical: Check this early to avoid KIU fallback for these specific formats
    web_parser = WebReceiptParser()
    if web_parser.can_parse(plain_text):
         logger.info("Detección: WebReceipt candidate matched.")
         res = web_parser.parse(plain_text)
         if res: 
             logger.info("Detectado WebReceipt (Avior/Estelar/Rutaca)")
             return res
         logger.info("WebReceiptParser abortó (None). Continuando...")

    # 2. COPA SPRK (Accelya/Sprite) - Robust detection
    if ('COPA AIRLINES' in plain_text_upper or 'ACCELYA' in plain_text_upper) and \
       ('RECORD LOCATOR' in plain_text_upper or 'LOCALIZADOR DE RESERVA' in plain_text_upper or 'AHNEQU' in plain_text_upper or 'ITINERARIO' in plain_text_upper): 
        logger.info("Detección: COPA SPRK candidate matched.")
        from core.parsers.copa_parser import CopaParser
        try:
            res = CopaParser().parse(plain_text)
            if res:
                return res.to_dict()
        except Exception as e:
            logger.error(f"Error parseando Copa: {e}")
        logger.info("CopaParser abortó (None o Error). Continuando...")
    
    if ('ETICKET RECEIPT' in plain_text_upper or 'RECIBO DE PASAJE' in plain_text_upper or 'RECIBO DE BOLETO' in plain_text_upper) and \
       ('RESERVATION CODE' in plain_text_upper or 'CODIGO DE RESERVA' in plain_text_upper or 'CODIGO DE RESERVACION' in plain_text_upper or 'CÓDIGO DE RESERVA' in plain_text_upper or 'CÓDIGO DE RESERVACIÓN' in plain_text_upper) and \
       'KIUSYS' not in plain_text_upper:
        logger.info("Detección: SABRE candidate matched.")
        try:
            res = SabreParser().parse(plain_text)
            if res:
                return res.to_dict()
        except Exception as e:
            logger.error(f"Error parseando Sabre: {e}")
        logger.info("SabreParser abortó (None o Error). Continuando...")

    if 'TK CONNECT' in plain_text_upper:
        logger.info("Detección: TK CONNECT candidate matched.")
        from core.parsers.tk_connect_parser import TKConnectParser
        try:
            res = TKConnectParser().parse(plain_text)
            if res:
                return res.to_dict()
        except Exception as e:
            logger.error(f"Error parseando TK Connect: {e}")
        
    if 'WINGO' in plain_text_upper:
        logger.info("Detección: WINGO candidate matched.")
        from core.parsers.wingo_parser import WingoParser
        try:
            res = WingoParser().parse(plain_text)
            if res:
                return res.to_dict()
        except Exception as e:
            logger.error(f"Error parseando Wingo: {e}")

    if 'AMADEUS' in plain_text_upper or 'CHECKMYTRIP' in plain_text_upper:
        logger.info("Detección: AMADEUS candidate matched.")
        try:
            res = _parse_amadeus_ticket(plain_text)
            if res: return res
        except Exception as e:
            logger.error(f"Error parseando Amadeus: {e}")

    # Fallback si nada coincide, buscamos si es un KIU válido aunque no tenga marcas claras
    res_final = None
    if 'PASSENGER' in plain_text_upper or 'ITINERARY' in plain_text_upper or 'KIUSYS' in plain_text_upper:
        logger.info("Detectado KIU/Compatible (Fallback)")
        res_final = _parse_kiu_ticket(plain_text, html_text)
    else:
        # Final Fallback
        logger.warning("No se detectó ningún formato conocido.")
        res_final = {"error": "Formato de boleto no reconocido o no soportado."}

    # 🛡️ NORMALIZACIÓN FINAL PARA TODOS LOS PARSERS
    if res_final and "error" not in res_final:
        if isinstance(res_final, dict) and res_final.get('is_multi_pax'):
            # Filtrar cada ticket individualmente
            res_final['tickets'] = [_apply_universal_schema_filter(t) for t in res_final.get('tickets', [])]
        else:
            res_final = _apply_universal_schema_filter(res_final)
            
    return res_final

# Aplicar Filtro Universal a todos los retornos de extract_data_from_text
def _extract_and_filter(plain_text: str, html_text: str = "", pdf_path: Optional[str] = None) -> Dict[str, Any]:
    data = extract_data_from_text(plain_text, html_text, pdf_path)
    return _apply_universal_schema_filter(data)

# --- GENERATE PDF ---

def generate_ticket(data: Dict[str, Any]) -> Tuple[bytes, str]:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    template_dir = os.path.join(base_dir, 'templates', 'core', 'tickets')
    source_system = data.get('SOURCE_SYSTEM', 'KIU').upper()
    
    env = Environment(loader=FileSystemLoader(template_dir), autoescape=select_autoescape(['html', 'xml']))
    
    # Load IATA resources locally
    airports_db = {}
    airlines_db = {}
    try:
        with open(os.path.join(base_dir, 'data', 'airlines.json'), 'r', encoding='utf-8') as f:
            airlines_db = json.load(f)
        with open(os.path.join(base_dir, 'data', 'airports.json'), 'r', encoding='utf-8') as f:
            airports_db = json.load(f)
    except Exception as e:
        logger.warning(f"Error loading IATA: {e}")

    # Template selection for KIU/Unified
    template_name = "ticket_template_kiu_bolivares.html"
    if 'AMADEUS' in source_system: 
        template_name = "ticket_template_amadeus.html"
    elif 'COPA' in source_system: 
        template_name = "ticket_template_copa_sprk.html"
    elif 'SABRE' in source_system:
        template_name = "ticket_template_sabre.html"
    
    # Prepare Context (KIU Logic Enhanced)
    vuelos = []
    for v in data.get('vuelos', []):
        new_v = v.copy()
        # Enrich
        if 'origen' in new_v and isinstance(new_v['origen'], str) and new_v['origen'] in airports_db: 
            new_v['origen'] = airports_db[new_v['origen']]
        if 'destino' in new_v and isinstance(new_v['destino'], str) and new_v['destino'] in airports_db: 
            new_v['destino'] = airports_db[new_v['destino']]
        if 'aerolinea' in new_v and isinstance(new_v['aerolinea'], str) and new_v['aerolinea'] in airlines_db: 
            new_v['aerolinea'] = airlines_db[new_v['aerolinea']]
        
        # Format Dates
        if 'fecha' not in new_v and 'departure_date' in new_v:
             try: new_v['fecha'] = dt.datetime.fromisoformat(new_v['departure_date']).strftime("%d%b").upper()
             except: pass
        if 'equipaje' in new_v: new_v['otras_notas'] = new_v['equipaje']
        
        vuelos.append(new_v)

    context = {
        'boleto': {
            'pasajero_nombre_completo': data.get('NOMBRE_DEL_PASAJERO') or data.get('passenger_name'),
            'solo_nombre_pasajero': data.get('SOLO_NOMBRE_PASAJERO') or data.get('solo_nombre_pasajero'),
            'codigo_identificacion': data.get('CODIGO_IDENTIFICACION') or data.get('FOID') or data.get('passenger_document'),
            'solo_codigo_reserva': data.get('SOLO_CODIGO_RESERVA') or data.get('CODIGO_RESERVA') or data.get('pnr'),
            'pnr': data.get('CODIGO_RESERVA') or data.get('pnr'),
            'numero_boleto': data.get('NUMERO_DE_BOLETO') or data.get('ticket_number'),
            'fecha_emision': data.get('FECHA_DE_EMISION') or data.get('fecha_emision'),
            'agente_emisor': data.get('AGENTE_EMISOR') or data.get('agencia'),
            'aerolinea': data.get('NOMBRE_AEROLINEA') or data.get('airline_name'),
            'direccion_aerolinea': data.get('DIRECCION_AEROLINEA'),
            'vuelos': vuelos,
            'ruta': data.get('ItinerarioFinalLimpio'),
            'tarifa': data.get('TARIFA') or data.get('TARIFA_IMPORTE'),
            'impuestos': data.get('IMPUESTOS'),
            'total': data.get('TOTAL') or data.get('TOTAL_IMPORTE'),
        },
        'pasajero': data.get('pasajero'),
        'reserva': data.get('reserva'),
        'itinerario': {'vuelos': vuelos},
        'solo_nombre_pasajero': data.get('SOLO_NOMBRE_PASAJERO') or data.get('solo_nombre_pasajero'),
        'agencia': data.get('agencia')
    }
    
    template = env.get_template(template_name)
    html_out = template.render(context)
    
    print("Generando PDF en memoria...")
    from weasyprint import HTML as WeasyHTML
    import io
    pdf_bytes = WeasyHTML(string=html_out).write_pdf()
    
    timestamp = dt.datetime.now().strftime("%Y%m%d%H%M%S")
    num_boleto = data.get('NUMERO_DE_BOLETO')
    if not num_boleto:
        num_boleto = "SIN_NUMERO"
    fname = f"Boleto_{num_boleto}_{timestamp}.pdf"
    return pdf_bytes, fname
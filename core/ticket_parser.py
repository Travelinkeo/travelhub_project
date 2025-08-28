# Archivo: core/ticket_parser.py

import re
import logging
from .identification_utils import normalize_codigo_identificacion, extract_codigo_identificacion_anywhere
from .utils import LOCATION_TOKENS, STOP_NAME_TOKENS  # Centralizamos tokens de ubicación y corte de nombre

logger = logging.getLogger(__name__)
import json
import datetime as dt
from decimal import Decimal, InvalidOperation
from typing import Dict, Any, List, Optional, Tuple

from jinja2 import Environment, FileSystemLoader, select_autoescape
from bs4 import BeautifulSoup
import os

# --- Funciones de Ayuda Generales ---

def _clean_value(value: Any) -> str:
    """Limpia un valor, convirtiéndolo a string y eliminando espacios sobrantes."""
    if value is None:
        return ''
    return str(value).strip()

def string_a_decimal(s: Optional[str], default: Decimal = Decimal('0.00')) -> Decimal:
    """Convierte un string a Decimal, manejando errores y formatos comunes."""
    if s is None:
        return default
    try:
        # Eliminar caracteres no numéricos excepto el punto decimal
        cleaned_s = re.sub(r'[^\d.]', '', s)
        return Decimal(cleaned_s)
    except (InvalidOperation, TypeError, ValueError):
        return default

def string_a_fecha(s: Optional[str]) -> Optional[dt.date]:
    """Convierte un string de fecha en varios formatos a un objeto date."""
    if not s:
        return None
    s = s.strip()
    # Mapa de meses en español a inglés
    month_map = {
        'ene': 'Jan', 'feb': 'Feb', 'mar': 'Mar', 'abr': 'Apr', 'may': 'May', 'jun': 'Jun',
        'jul': 'Jul', 'ago': 'Aug', 'sep': 'Sep', 'oct': 'Oct', 'nov': 'Nov', 'dic': 'Dec'
    }
    # Reemplazar de forma case-insensitive usando regex
    for es, en in month_map.items():
        s = re.sub(fr'\b{es}\b', en, s, flags=re.IGNORECASE)
    
    formatos_probables = [
        '%d %b %y',  # 08 may 25
        '%d %b %Y',  # 08 May 2025
        '%d/%m/%y',  # 08/05/25
        '%d/%m/%Y',  # 08/05/2025
        '%Y-%m-%d',  # 2025-05-08
    ]
    for fmt in formatos_probables:
        try:
            return dt.datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None

def _parse_currency_amount(value: str) -> Tuple[Optional[str], Optional[Decimal]]:
    """Intenta separar moneda (3 letras) y monto a Decimal de una cadena como 'USD 170.01' o 'USD      170.01'."""
    if not value or value == 'No encontrado':
        return None, None
    # Quitar espacios redundantes
    txt = re.sub(r'\s+', ' ', value.strip())
    m = re.match(r'^([A-Z]{3})\s+([0-9][0-9,\.]+)$', txt)
    if not m:
        # Intento alterno: moneda pegada al número
        m = re.match(r'^([A-Z]{3})([0-9][0-9,\.]+)$', txt)
    if m:
        currency = m.group(1)
        amount_raw = m.group(2).replace(',', '')
        try:
            amount = Decimal(amount_raw)
        except Exception:
            amount = None
        return currency, amount
    return None, None

def _extract_field(text: str, patterns: List[str], default: str = 'No encontrado') -> str:
    """Extrae un campo usando una lista de patrones regex."""
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            # Intenta obtener el primer grupo, si no, el match completo
            try:
                return match.group(1).strip()
            except IndexError:
                return match.group(0).strip()
    return default

def _extract_field_single_line(text: str, patterns: List[str], default: str = 'No encontrado') -> str:
    """Devuelve la primera coincidencia asegurando que sea sólo una línea."""
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            try:
                value = match.group(1)
            except IndexError:
                value = match.group(0)
            return value.splitlines()[0].strip()
    return default

# --- Lógica de Parseo Específica para KIU ---

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
    """Extrae el nombre completo (FORMATO: APELLIDO(S)/NOMBRE(S)).

    Problema reportado: En algunos correos el salto de línea entre la línea del nombre
    y la siguiente (ciudad / dirección) se pierde (p.ej. en HTML a texto plano) y se
    termina agregando algo como "DUQUE ECHEVERRY/OSCA (CIUDAD DE PANAMA)" o
    "DUQUE ECHEVERRY/OSCA (FLORIDA)" dentro del mismo match.

    Estrategia defensiva:
    1. Capturar la línea con un patrón más permisivo (permitimos paréntesis y comas temporalmente).
    2. Cortar si aparece un paréntesis de apertura "(" después del patrón básico APELLIDO/NAME.
    3. Cortar si aparecen tokens que claramente pertenecen al siguiente campo: FOID, ADDRESS,
       ISSUE, NIT, TICKET, OFFICE ID, TELEPHONE, MAIL INFO, etc.
    4. Normalizar espacios y retornar sólo la parte pura del nombre (sin sufijos de ciudad).
    """
    raw = _extract_field_single_line(texto, [
        r'NAME/NOMBRE\s*[:\s]*([A-ZÁÉÍÓÚÑ/ (),.-]{3,})',
        r'NAME\s*[:\s]*([A-ZÁÉÍÓÚÑ/ (),.-]{3,})'
    ])
    if raw == 'No encontrado':
        return raw

    upper_raw = raw.upper()

    # Tokens que NO deben formar parte del nombre si aparecen luego en la misma línea
    # Tokens centralizados para cortar si aparecen tras el nombre
    stop_tokens = STOP_NAME_TOKENS

    cut_positions = []
    for token in stop_tokens:
        idx = upper_raw.find(token)
        if idx != -1 and idx > 5:  # >5 para evitar cortes espurios muy al inicio
            cut_positions.append(idx)

    # También cortar si aparece un paréntesis de apertura (ciudad) después de un mínimo de 4 chars
    par_idx = raw.find('(')
    if par_idx != -1 and par_idx > 4:
        cut_positions.append(par_idx)

    if cut_positions:
        raw = raw[:min(cut_positions)].rstrip()

    # Normalización básica de caracteres
    raw = re.sub(r'[^A-ZÁÉÍÓÚÑ/ ]+', ' ', raw.upper())
    raw = re.sub(r'\s{2,}', ' ', raw).strip()

    # Si no hay '/', devolver (no intentamos heurísticas adicionales)
    if '/' not in raw:
        return raw

    apellidos, nombres = raw.split('/', 1)
    nombres = nombres.strip()

    # --- Nueva lógica: remover contaminación de tokens de ubicación planos ---
    # Usamos tokens centralizados (convertimos a set para eficiencia)
    LOCATION_TOKENS_SET = {t.upper() for t in LOCATION_TOKENS}

    # 1) Eliminar patrón final "CIUDAD DE <PALABRAS>" completo
    nombres = re.sub(r'(?:CIUDAD DE [A-ZÁÉÍÓÚÑ]{2,}(?:\s+[A-ZÁÉÍÓÚÑ]{2,})*)$', '', nombres).strip()

    # 2) Tokenizar y si desde un índice >=1 todos los tokens restantes son de ubicación, cortar ahí
    tokens = nombres.split()
    if len(tokens) > 1:
        for i in range(1, len(tokens)):
            tail = tokens[i:]
            if tail and all(t in LOCATION_TOKENS_SET for t in tail):
                tokens = tokens[:i]
                break
        else:
            # Si no se cortó, pero el último token es de ubicación único, quitarlo (caso "OSCA FLORIDA")
            if tokens[-1] in LOCATION_TOKENS_SET:
                tokens = tokens[:-1]
    nombres_limpios = ' '.join(tokens)

    # 3) Normalización espacios finales
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
    noise_patterns = [
        r'PARA MAYOR INFORMACION', r'VALIDEZ DEL BOLETO', r'CONDICIONES DE BOLETOS', r'FOR YOUR ENTRY OR DEPARTURE',
        r'________________________________', r'SEND BY AGENT', r'EL PASAJERO DEBE ESTAR PRESENTE', r'CONDICIONES DEL BOLETO',
        r'CONDICIONES DE TRANSPORTE', r'INFORMACION IMPORTANTE', r'EQUIPAJE PERMITIDO', r'VUELOS NACIONALES',
        r'VUELOS INTERNACIONALES', r'EXCESOS DE EQUIPAJE', r'PENALIDADES', r'EL PASAJERO DEBERA PRESENTARSE',
        r'EL PASAJERO ES RESPONSABLE DE TODOS LOS DOCUMENTOS', r'FRANQUICIA DE EQUIPAJE', r'MEDIDAS GENERALES DE BIOSEGURIDAD',
        r'DESTINOS NACIONALES', r'DESTINOS INTERNACIONALES', r'EL SERVICIO DE TRANSPORTE REALIZADO POR',
        r'LA EMPRESA SE REGIRA POR LAS REGULACIONES', r'SE DEBE CUMPLIR CON LOS REQUERIMIENTOS MIGRATORIOS',
        r'LA LINEA NO SE HACE RESPONSABLE POR CONEXIONES', r'EL BOLETO AEREO NO ES REEMBOLSABLE', r'TO GET INTO COSTA RICA',
        r'DILIGENCIAR EL FORMULARIO', r'EL CLIENTE DEBE PERMANECER', r'PRESENTAR ORIGINAL Y COPIA',
        r'EL ROTULADO Y LA ENTREGA DEL EQUIPAJE', r'LOS EQUIPOS DEPORTIVOS', r'EL DIA DEL VUELO EL EQUIPAJE ADICIONAL',
        r'ESTE BOLETO ES VALIDO POR', r'NO REEMBOLSABLE, NO TRANSFERIBLE', r'PARA INGRESAR A ARUBA', r'VALIDO POR 365 DIAS',
        r'LAS TARIFAS ESTAN SUJETAS A CAMBIOS', r'ALGUNAS CONDICIONES Y RESTRICCIONES', r'CAMBIOS AL ITINERARIO',
        r'EN CASO DE NO PRESENTARSE', r'DEBEN PRESENTARSE EN EL MOSTRADOR', r'EQUIPAJE DE MANO PERMITIDO',
        r'EQUIPAJE FACTURADO PERMITIDO', r'EQUIPAJE COMPARTIDO', r'EQUIPAJE ADICIONAL', r'SI EL PASAJERO NO VA A VIAJAR',
        r'DISPONIBILIDADES Y TARIFAS', r'CONTRATO DE BOLETO', r'GRACIAS POR ELEGIR VOLAR CON NOSOTROS', r'AHORA PIDE TU RIDERY',
        r'LOS PASAJEROS DEBEN PRESENTARSE', r'LA VALIDEZ DE ESTE BOLETO', r'NOTA IMPORTANTE', r'SE RECOMIENDA RECONFIRMAR',
        r'SI SU VIAJE INCLUYE', r'TRANSPORTE AEREO DE CABOTAJE', r'APLICABLE AL TRANSPORTE AEREO INTERNACIONAL',
        r'CON LA COMPRA DEL BOLETO', r'VUELOS LSP/CUR/LSP OPERADOS POR', r'EN LOS VUELOS LSP/CUR/LSP PARA RECLAMOS',
        r'SE PROHIBE LLEVAR A BORDO', r'PARA LAS RUTAS CCS/LRV/CCS', r'PARA LA RUTA CCS/SJO/CCS', r'PARA INGRESAR A COSTA RICA',
        r'LAS CONDICIONES GENERALES DE ESTE CONTRATO', r'ALBATROS SE APEGA AL CUMPLIMIENTO', r'DESDE/HACIA\s+VUELO\s+CL\s+FECHA\s+HORA\s+HORA\s+BASE\s+TARIFARIA\s+EQP\.\s+ESTATUS',
        r'EN RUTAS INTERNACIONALES CUATRO \(04\) HORAS ANTES', r'EN RUTAS NACIONALES DOS \(02\) HORAS ANTES'
    ]
    if html_text:
        try:
            soup = BeautifulSoup(html_text, 'html.parser')
            pre_tags = soup.find_all('pre')
            start_keywords = ['FROM/TO', 'DESDE/HACIA']
            end_keywords = ['ENDORSEMENTS', 'CONDICIONES', 'FARE CALC', 'TOUR CODE', 'PAYMENT', 'VALIDEZ DEL BOLETO', 'INFORMACION IMPORTANTE', 'BAGGAGE', 'CONTRATO DE BOLETO', 'GRACIAS POR ELEGIR VOLAR CON NOSOTROS', 'AHORA PIDE TU RIDERY']
            capturing = False
            itinerary_lines = []
            for tag in pre_tags:
                lines_in_tag = tag.get_text().splitlines()
                for line in lines_in_tag:
                    stripped_line = line.strip()
                    if not stripped_line: continue
                    is_noise = any(re.search(np, stripped_line, re.IGNORECASE) for np in noise_patterns)
                    if is_noise: continue
                    if not capturing and any(keyword in stripped_line.upper() for keyword in start_keywords) and ('FLIGHT' in stripped_line.upper() or 'VUELO' in stripped_line.upper()):
                        capturing = True
                        continue 
                    if capturing:
                        if any(keyword in stripped_line.upper() for keyword in end_keywords):
                            capturing = False
                            break
                        itinerary_lines.append(stripped_line)
                if not capturing and itinerary_lines:
                    break
            if itinerary_lines:
                final_html_itinerary = [line for line in itinerary_lines if line.strip()]
                # Filtros de corte / limpieza finales (evitar que se cuele texto de condiciones)
                stop_triggers = [
                    r'^PERO SI', r'^CONDICIONES', r'^NOTA', r'^EL PASAJERO', r'^PARA MAYOR', r'^SI EL PASAJERO',
                    r'^EN CASO', r'^CAMBIOS AL', r'^NO REEMBOLSABLE', r'^GRACIAS POR', r'^AHORA PIDE'
                ]
                cleaned_html = []
                for l in final_html_itinerary:
                    upper = l.upper()
                    if any(re.search(pat, upper, re.IGNORECASE) for pat in stop_triggers):
                        break
                    cleaned_html.append(l)
                if cleaned_html:
                    logger.debug("Itinerario extraído exitosamente desde HTML.")
                    return '\n'.join(cleaned_html)
        except Exception as e:
            logger.exception("Error durante la extracción HTML; intentando fallback a texto plano.")
    logger.warning("No se encontró itinerario HTML válido; usando método de texto plano.")
    lines = plain_text.splitlines()
    itinerary_data_lines = []
    capturing = False
    flight_line_patterns = [r'^[A-Z]{3}\s+[A-Z0-9]+\s+[A-Z0-9]+\s+\d{1,2}[A-Z]{3}', r'^[A-Z]{3}\s+[A-Z0-9]+\s+[A-Z]{3}', r'^[A-Z]{2,}\s+[A-Z0-9]+\s+[A-Z0-9]+\s+\d{1,2}[A-Z]{3}', r'^X\s+[A-Z]{3}\s+[A-Z0-9]+']
    for line in lines:
        stripped_line = line.strip()
        if not stripped_line: continue
        is_noise = any(re.search(np, stripped_line, re.IGNORECASE) for np in noise_patterns)
        if is_noise:
            if capturing:
                capturing = False
            continue
        if not capturing:
            if any(re.search(pattern, stripped_line, re.IGNORECASE) for pattern in flight_line_patterns):
                capturing = True
                itinerary_data_lines.append(stripped_line)
        else:
            itinerary_data_lines.append(stripped_line)
    # Post-filtrado en modo texto plano
    stop_triggers = [
        r'^PERO SI', r'^CONDICIONES', r'^NOTA', r'^EL PASAJERO', r'^PARA MAYOR', r'^SI EL PASAJERO',
        r'^EN CASO', r'^CAMBIOS AL', r'^NO REEMBOLSABLE', r'^GRACIAS POR', r'^AHORA PIDE'
    ]
    cleaned_plain = []
    for l in itinerary_data_lines:
        if any(re.search(pat, l.upper(), re.IGNORECASE) for pat in stop_triggers):
            break
        cleaned_plain.append(l)
    return "\n".join(cleaned_plain) if cleaned_plain else ("\n".join(itinerary_data_lines) if itinerary_data_lines else "No se pudo procesar el itinerario.")

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
    """Extrae el nombre de la aerolínea emisora en KIU evitando que se 'pegue' la línea siguiente.

    Problema observado: en algunos boletos KIU (ej. RUTAS AEREAS DE VENEZUELA RAV, SA)
    la línea siguiente (p.ej. comienzo de ADDRESS o ISSUE DATE) queda justo a continuación
    sin salto detectado y el regex simple captura demasiado.

    Estrategia:
    1. Capturar línea completa cruda con regex amplio (una sola línea via _extract_field_single_line).
    2. Post-procesar: si después del nombre se detectan secuencias que pertenezcan claramente a otro campo
       (ADDRESS, ISSUE, BOOKING REF, NAME/, FOID, TICKET, AIR FARE, TAX, TOTAL, DESDE/HACIA, FROM/TO, C1/PNR)
       se cortará antes de ese marcador.
    3. Limpiar puntuación sobrante (comas repetidas, espacios).
    4. Asegurar que termina en letra (si termina en coma se mantiene; si termina en palabra seguida de coma y algo raro, cortar).
    """
    raw = _extract_field_single_line(texto, [
        r'ISSUING AIRLINE/LINEA AEREA EMISORA\s*[:\s]*([A-Z0-9 ,.&-]{3,})',
        r'ISSUING AIRLINE\s*[:\s]*([A-Z0-9 ,.&-]{3,})'
    ])
    if raw == 'No encontrado':
        return raw
    # Marcadores que no deben formar parte del nombre de la aerolínea (precedidos por espacio para evitar falsos positivos dentro de palabras)
    stop_tokens = [
        ' ADDRESS', ' ISSUE', ' BOOKING REF', ' NAME/', ' FOID', ' TICKET', ' AIR FARE', ' TAX', ' TOTAL',
        ' DESDE/HACIA', ' FROM/TO', ' C1/'
    ]
    upper_raw = raw.upper()
    cut_positions: List[int] = []
    for token in stop_tokens:
        idx = upper_raw.find(token)
        if idx > 5:  # evitar corte si está muy al inicio
            cut_positions.append(idx)
    # También cortar si aparece un paréntesis inesperado (raro pero defensivo)
    par_idx = raw.find('(')
    if par_idx != -1 and par_idx > 4:
        cut_positions.append(par_idx)
    if cut_positions:
        raw = raw[:min(cut_positions)].rstrip()
    # Limpiezas: espacios múltiples y comas redundantes
    raw = re.sub(r'\s{2,}', ' ', raw)
    raw = re.sub(r',\s*,+', ', ', raw)
    # Re-corte defensivo si aún quedaron tokens residuales parcialmente
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
    """Parsea el contenido de un boleto KIU y devuelve un diccionario estructurado.

    Esta implementación proviene de la versión funcional en external_ticket_generator/KIU/main (3).py
    y devuelve claves compatibles con el resto del sistema (p. ej. 'NUMERO_DE_BOLETO', 'ItinerarioFinalLimpio', etc.).
    """
    logger.info("Iniciando extracción de datos (KIU)...")
    nombre_completo = _get_nombre_completo_pasajero(plain_text)
    solo_codigo = _get_solo_codigo_reserva(plain_text)
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
        'NOMBRE_AEROLINEA': _get_nombre_aerolinea(plain_text),
        'DIRECCION_AEROLINEA': _get_direccion_aerolinea(plain_text),
        'TARIFA': _get_tarifa(plain_text),
        'IMPUESTOS': _get_impuestos(plain_text),
        'TOTAL': _get_total(plain_text),
        'ItinerarioFinalLimpio': _extraer_itinerario_kiu(plain_text, html_text),
    }
    # Normalización monetaria adicional
    tarifa_moneda, tarifa_importe = _parse_currency_amount(data['TARIFA'])
    total_moneda, total_importe = _parse_currency_amount(data['TOTAL'])
    data['TARIFA_MONEDA'] = tarifa_moneda
    data['TARIFA_IMPORTE'] = str(tarifa_importe) if tarifa_importe is not None else None
    data['TOTAL_MONEDA'] = total_moneda
    data['TOTAL_IMPORTE'] = str(total_importe) if total_importe is not None else None
    logger.info("Datos KIU extraídos y normalizados correctamente.")
    return data

# --- Lógica de Parseo Específica para SABRE ---

def _parsear_itinerario_sabre_mejorado(itinerario_texto: str) -> List[Dict[str, Any]]:
    """Refactorización para manejar múltiples vuelos en Sabre."""
    vuelos: List[Dict[str, Any]] = []
    if not itinerario_texto:
        return vuelos

    # Normalizar saltos y remover duplicados de espacios para heurísticas (sin perder info original para extracción puntual)
    texto = itinerario_texto.replace('\r', '')

    # Estrategia: dividir por patrones que indican inicio de segmento:
    # 1) Linea que inicia con fecha 'dd Mmm dd'
    # 2) 'Departure:' (multi-tramo con Bloques 'Departure:' / 'Arrival:')
    pattern_split = r'(?=^\s*(?:\d{1,2}\s+\w{3}\s+\d{2}|Departure:\s*\d{1,2}\s+\w{3}\s+\d{2}))'
    bloques = re.split(pattern_split, texto, flags=re.MULTILINE)

    # No existe límite artificial de segmentos; se añade cada bloque válido encontrado.
    for bloque in bloques:
        b = bloque.strip()
        if not b:
            continue
        # Debe contener al menos un número de vuelo (AA 123, AF 435, etc.) y un aeropuerto
        if not re.search(r'\b[A-Z]{2}\s?\d{1,4}\b', b):
            continue

        vuelo: Dict[str, Any] = {}
        # Fecha salida: priorizar 'Departure:' luego fecha al inicio
        m = re.search(r'Departure:\s*(\d{1,2}\s+\w{3}\s+\d{2})', b)
        if m:
            vuelo['fecha_salida'] = m.group(1)
        else:
            m = re.search(r'^(\d{1,2}\s+\w{3}\s+\d{2})', b)
            if m:
                vuelo['fecha_salida'] = m.group(1)

        m = re.search(r'Arrival:\s*(\d{1,2}\s+\w{3}\s+\d{2})', b)
        if m:
            vuelo['fecha_llegada'] = m.group(1)

        # Número de vuelo: línea sola o con prefijo
        m = re.search(r'\b([A-Z]{2}\s?\d{1,4})\b', b)
        if m:
            vuelo['numero_vuelo'] = m.group(1).replace(' ', '') if len(m.group(1)) <= 3 else m.group(1).strip()

        # Aerolínea (línea previa al número de vuelo o 'Operated by')
        aerolinea = ''
        lines = [ln.strip() for ln in b.splitlines() if ln.strip()]
        for i, ln in enumerate(lines):
            if re.fullmatch(r'[A-Z]{2}\s?\d{1,4}', ln):
                # línea previa podría ser aerolínea
                if i > 0:
                    prev = lines[i-1]
                    if len(prev.split()) >= 1 and not re.search(r'\d{1,2}:\d{2}', prev):
                        aerolinea = prev
                break
        if not aerolinea:
            m = re.search(r'Operated by:\s*\n?([A-Z0-9 \-]+)', b, re.IGNORECASE)
            if m:
                aerolinea = m.group(1).strip()
        vuelo['aerolinea'] = aerolinea

        # Origen / destino: buscar primeras dos líneas tipo 'CIUDAD, PAIS'
        ciudades = re.findall(r'([A-ZÁÉÍÓÚ0-9 \-]+,\s*[A-ZÁÉÍÓÚ0-9 \-]+)', b)
        if len(ciudades) >= 2:
            vuelo['origen'] = {'ciudad': ciudades[0].split(',')[0].strip(), 'pais': ciudades[0].split(',')[1].strip()}
            vuelo['destino'] = {'ciudad': ciudades[1].split(',')[0].strip(), 'pais': ciudades[1].split(',')[1].strip()}

        # Horas (primeras dos ocurrencias)
        horas = re.findall(r'(\d{1,2}:\d{2})', b)
        if len(horas) >= 2:
            vuelo['hora_salida'] = horas[0]
            vuelo['hora_llegada'] = horas[1]

        # Terminales (tomar dos primeros si existen)
        terminals = re.findall(r'Terminal\s*\n?([A-Z0-9 \-]+)', b, flags=re.IGNORECASE)
        if len(terminals) >= 1:
            vuelo['terminal_salida'] = terminals[0].strip()
        if len(terminals) >= 2:
            vuelo['terminal_llegada'] = terminals[1].strip()

        # Cabina
        m = re.search(r'Cabin\s+([A-Za-z]+)', b)
        if m:
            vuelo['cabina'] = m.group(1)
        # Equipaje
        m = re.search(r'Baggage Allowance\s*([A-Z0-9]+)', b)
        if m:
            vuelo['equipaje'] = m.group(1)
        # PNR local dentro del bloque
        m = re.search(r'Airline Reservation Code\s*([A-Z0-9]+)', b)
        if m:
            vuelo['codigo_reservacion_local'] = m.group(1)

        # Validar mínimos
        if vuelo.get('numero_vuelo') and vuelo.get('origen') and vuelo.get('destino'):
            vuelos.append(vuelo)

    return vuelos

def _formatear_fecha_dd_mm_yyyy(fecha_str: str) -> str:
    """Convierte una fecha estilo '13 Aug 25' o '13 Aug 2025' a formato DD-MM-YYYY. Si falla devuelve la original."""
    if not fecha_str:
        return fecha_str
    fecha_str = fecha_str.strip()
    formatos = ['%d %b %y', '%d %b %Y', '%Y-%m-%d']
    for fmt in formatos:
        try:
            dt_obj = dt.datetime.strptime(fecha_str, fmt)
            return dt_obj.strftime('%d-%m-%Y')
        except ValueError:
            continue
    return fecha_str

def _inferir_fecha_llegada(fecha_salida: str, hora_salida: str, hora_llegada: str, fecha_llegada_existente: Optional[str]) -> str:
    """Devuelve fecha_llegada en DD-MM-YYYY: usa la existente si ya viene; si no, asume mismo día o +1 si hora_llegada < hora_salida."""
    if fecha_llegada_existente:
        return _formatear_fecha_dd_mm_yyyy(fecha_llegada_existente)
    if not fecha_salida:
        return ''
    try:
        base = dt.datetime.strptime(_formatear_fecha_dd_mm_yyyy(fecha_salida), '%d-%m-%Y')
    except Exception:
        return ''
    if hora_salida and hora_llegada:
        try:
            hs = dt.datetime.strptime(hora_salida, '%H:%M')
            hl = dt.datetime.strptime(hora_llegada, '%H:%M')
            if hl < hs:
                base = base + dt.timedelta(days=1)
        except Exception:
            pass
    return base.strftime('%d-%m-%Y')

def _fecha_a_iso(fecha_str: str) -> Optional[str]:
    """Convierte cadena de fecha conocida a ISO (YYYY-MM-DD) si es posible."""
    if not fecha_str:
        return None
    original = fecha_str.strip()
    # Intentar primero si ya viene en DD-MM-YYYY
    for fmt in ('%d-%m-%Y', '%d %b %y', '%d %b %Y', '%Y-%m-%d'):
        try:
            dt_obj = dt.datetime.strptime(original, fmt)
            return dt_obj.strftime('%Y-%m-%d')
        except ValueError:
            continue
    return None

def _parse_sabre_ticket(plain_text: str) -> Dict[str, Any]:
    """Parsea el contenido de un boleto Sabre y devuelve un diccionario estructurado.

    Mejoras:
    - Extrae documento_identidad: texto entre corchetes tras el nombre [AS639110]
    - Formatea fechas a DD-MM-YYYY (fecha_emision, fechas de vuelos)
    - Si falta fecha_llegada de un segmento, se infiere (misma fecha o +1 si cruza medianoche)
    - Soporta número ilimitado de segmentos (no recorta lista)
    """
    
    # Extraer datos generales
    import os
    pasajero_raw = _extract_field(plain_text, [r'Prepared For\s*([A-ZÁÉÍÓÚ/\s]+)'])
    # documento identidad dentro de corchetes tras el nombre
    documento_identidad = _extract_field(plain_text, [r'Prepared For\s*[A-ZÁÉÍÓÚ/\s]+\s*\[([A-Z0-9]+)\]'], default='') or '-'
    
    itinerario_raw = _extract_field(plain_text, [r'Itinerary Details(.*?)(?=Please contact your travel arranger)'])

    data = {
        'SOURCE_SYSTEM': 'SABRE',
        'preparado_para': pasajero_raw,
        'SOLO_NOMBRE_PASAJERO': pasajero_raw.split('/')[0].strip() if '/' in pasajero_raw else pasajero_raw,
        'codigo_reservacion': _extract_field(plain_text, [r'Reservation Code\s+([A-Z0-9]+)']),
        'fecha_emision': _extract_field(plain_text, [r'Issue Date\s+([\d\w\s]+)']),
        'numero_boleto': _extract_field(plain_text, [r'Ticket Number\s+(\d+)']),
        'aerolinea_emisora': _extract_field(plain_text, [r'Issuing Airline\s+(.+?)\n']),
        'agente_emisor': _extract_field(plain_text, [r'Issuing Agent\s+(.+?)\n']),
        'numero_iata': _extract_field(plain_text, [r'IATA Number\s+(\d+)']),
        'numero_cliente': _extract_field(plain_text, [r'Customer Number\s+([A-Z0-9]+)']),
        'vuelos': _parsear_itinerario_sabre_mejorado(itinerario_raw),
        'errores': []
    }
    # Intentar cargar el parser externo por ruta para reutilizar su lógica robusta
    sabre_module = None
    try:
        import importlib.util
        sabre_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'external_ticket_generator', 'SABRE', 'parsear_vuelo_universal.py')
        if os.path.exists(sabre_path):
            spec = importlib.util.spec_from_file_location('sabre_parser_external', sabre_path)
            sabre_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(sabre_module)
    except Exception:
        sabre_module = None

    vuelos = []
    if sabre_module:
        try:
            fmt = 'block'
            if hasattr(sabre_module, 'detect_format'):
                fmt = sabre_module.detect_format(plain_text)
            if fmt == 'tabular' and hasattr(sabre_module, 'parse_tabular'):
                vuelos = sabre_module.parse_tabular(plain_text)
            elif hasattr(sabre_module, 'parse_block'):
                vuelos = sabre_module.parse_block(plain_text)
        except Exception:
            vuelos = []

    # Si no obtuvimos vuelos del módulo externo, usar el parser interno como fallback
    if not vuelos:
        # Extraer datos generales usando lógica interna
        pasajero_raw = _extract_field(plain_text, [r'Prepared For\s*([A-ZÁÉÍÓÚ/\s]+)'])
        itinerario_raw = _extract_field(plain_text, [r'Itinerary Details(.*?)(?=Please contact your travel arranger)'])
        vuelos = _parsear_itinerario_sabre_mejorado(itinerario_raw)
    else:
        # Si usamos el parser externo, normalizamos algunos campos para la plantilla
        # (el módulo externo devuelve listas de dicts con claves variadas)
        pass

    # Extraer otros campos comunes
    nombre_pasajero = _extract_field(plain_text, [r'(?:Prepared For|Preparado para)\s*\n\s*([A-ZÁÉÍÓÚ0-9\-\/\s,\.]+?)(?:\s*\[|\n|$)'], default='')
    codigo_reservacion = _extract_field(plain_text, [r'(?:Reservation Code|C[ÓO]DIGO DE RESERVA)\s*[:\t\s]*([A-Z0-9]+)'], default='')
    fecha_emision = _extract_field(plain_text, [r'(?:Issue Date|Fecha de Emisi[oó]n|FECHA DE EMISIÓN)\s*[:\t\s]*([\d]{1,2} \w{3} [\d]{2})'], default='')
    numero_boleto = _extract_field(plain_text, [r'(?:Ticket Number|N[ÚU]MERO DE BOLETO)\s*[:\t\s]*([\d]+)'], default='')
    aerolinea_emisora = _extract_field(plain_text, [r'(?:Issuing Airline|AEROL[ÍI]NEA EMISORA)\s*[:\t\s]*([A-ZÁÉÍÓÚ0-9 \/]+)'], default='')
    agente_emisor = _extract_field(plain_text, [r'(?:Issuing Agent|AGENTE EMISOR)\s*[:\t\s]*([^\n\r]+)'], default='')
    numero_iata = _extract_field(plain_text, [r'(?:IATA Number|IATA)\s*[:\t\s]*([\d]+)'], default='')
    numero_cliente = _extract_field(plain_text, [r'(?:Customer Number|Customer|N[ÚU]MERO DE CLIENTE)\s*[:\t\s]*([A-Z0-9]+)'], default='')

    agente_emisor = agente_emisor.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
    agente_emisor = agente_emisor.split('Issuing Agent Location')[0].strip() if agente_emisor else agente_emisor

    fecha_emision_fmt = _formatear_fecha_dd_mm_yyyy(fecha_emision)
    fecha_emision_iso = _fecha_a_iso(fecha_emision_fmt) or _fecha_a_iso(fecha_emision)
    # Formatear fechas de vuelos y completar fecha_llegada
    vuelos_fmt = []
    for v in vuelos:
        fs_raw = v.get('fecha_salida', '')
        fl_raw = v.get('fecha_llegada', '')
        hs = v.get('hora_salida')
        hl = v.get('hora_llegada')
        fs = _formatear_fecha_dd_mm_yyyy(fs_raw)
        fl = _inferir_fecha_llegada(fs_raw, hs, hl, fl_raw)
        v['fecha_salida'] = fs
        v['fecha_llegada'] = fl
        v['fecha_salida_iso'] = _fecha_a_iso(fs) or _fecha_a_iso(fs_raw)
        v['fecha_llegada_iso'] = _fecha_a_iso(fl) or _fecha_a_iso(fl_raw)
        # Normalizar CO2 si existe (ej: "397.86 kg CO2")
        co2_raw = v.get('co2') or v.get('CO2')
        if co2_raw:
            mco2 = re.search(r'([0-9]+[0-9.,]*)\s*([A-Za-z]+)\s*CO2', co2_raw)
            if mco2:
                valor = mco2.group(1).replace(',', '')
                unidad = mco2.group(2)
                v['co2_valor'] = valor
                v['co2_unidad'] = unidad
            else:
                # fallback simple: extraer número
                mnum = re.search(r'([0-9]+[0-9.,]*)', co2_raw)
                if mnum:
                    v['co2_valor'] = mnum.group(1).replace(',', '')
                    v['co2_unidad'] = 'kg'
        vuelos_fmt.append(v)

    data = {
        'SOURCE_SYSTEM': 'SABRE',
        'preparado_para': nombre_pasajero,
    'documento_identidad': documento_identidad or '-',
        'SOLO_NOMBRE_PASAJERO': nombre_pasajero.split('/')[0].strip() if '/' in nombre_pasajero else nombre_pasajero,
        'codigo_reservacion': codigo_reservacion,
        'fecha_emision': fecha_emision_fmt,
    'numero_boleto': numero_boleto,
        'aerolinea_emisora': aerolinea_emisora,
        'agente_emisor': agente_emisor,
        'numero_iata': numero_iata,
        'numero_cliente': numero_cliente,
    'fecha_emision_iso': fecha_emision_iso,
        'vuelos': vuelos_fmt,
        'errores': []
    }
    # Intentar extraer fare / total si existieran etiquetas estándar
    fare_raw = _extract_field(plain_text, [r'Fare\s+([A-Z]{3}\s*[0-9,.]+)'])
    total_raw = _extract_field(plain_text, [r'Total\s+([A-Z]{3}\s*[0-9,.]+)'])
    # Patrones adicionales (algunos recibos usan "Grand Total" o "Amount Paid")
    if fare_raw in (None, '', 'No encontrado'):
        fare_raw = _extract_field(plain_text, [r'Air *Fare\s*[:]?\s*([A-Z]{3}\s*[0-9,.]+)'])
    if total_raw in (None, '', 'No encontrado'):
        total_raw = _extract_field(plain_text, [r'Grand Total\s*[:]?\s*([A-Z]{3}\s*[0-9,.]+)', r'Amount Paid\s*[:]?\s*([A-Z]{3}\s*[0-9,.]+)'])
    fare_cur, fare_amt = _parse_currency_amount(fare_raw)
    total_cur, total_amt = _parse_currency_amount(total_raw)
    data['fare'] = fare_raw if fare_raw not in (None, '', 'No encontrado') else None
    data['fare_currency'] = fare_cur
    data['fare_amount'] = str(fare_amt) if fare_amt is not None else None
    data['total'] = total_raw if total_raw not in (None, '', 'No encontrado') else None
    data['total_currency'] = total_cur
    data['total_amount'] = str(total_amt) if total_amt is not None else None

    return data

# --- Lógica de Parseo para Amadeus y Travelport (Placeholders) ---

def _parse_amadeus_ticket(plain_text: str) -> Dict[str, Any]:
    return {"SOURCE_SYSTEM": "AMADEUS", "error": "Parser para Amadeus no implementado."}

def _parse_travelport_ticket(plain_text: str) -> Dict[str, Any]:
    return {"SOURCE_SYSTEM": "TRAVELPORT", "error": "Parser para Travelport no implementado."}


# --- PUNTO DE ENTRADA PRINCIPAL ---

def extract_data_from_text(plain_text: str, html_text: str = "", pdf_path: Optional[str] = None) -> Dict[str, Any]:
    """Detecta el GDS del boleto a partir del texto y llama al parser correspondiente.

    Mejora: primero intenta detectar SABRE para evitar falsos positivos de KIU (ambos comparten frases como 'ISSUE DATE').
    La heurística KIU ahora requiere al menos un marcador distintivo (BOOKING REF, C1/PNR, ELECTRONIC TICKET header, KIUSYS).
    """
    plain_text_upper = plain_text.upper()

    # Heurística SABRE (orden primero)
    found_sabre = any([
        'ITINERARY DETAILS' in plain_text_upper,
        'PREPARED FOR' in plain_text_upper and 'RESERVATION CODE' in plain_text_upper,
        'ETICKET RECEIPT' in plain_text_upper and 'RESERVATION CODE' in plain_text_upper,
    ])
    if found_sabre:
        logger.info("Detectado GDS: SABRE (parser sabre activado)")
        return _parse_sabre_ticket(plain_text)

    # Heurística KIU (más restrictiva para evitar capturar SABRE)
    found_kiu = any([
        'KIUSYS.COM' in plain_text_upper,
        'E-TICKET ITINERARY RECEIPT' in plain_text_upper,
        'BOOKING REF' in plain_text_upper,
        re.search(r'\bC1/[A-Z0-9]{6}\b', plain_text_upper) is not None,
        ('ISSUE DATE/FECHA DE EMIS' in plain_text_upper and 'PASSENGER ITINERARY RECEIPT' in plain_text_upper),
    ])
    logger.debug("Heurística KIU evaluada=%s", found_kiu)
    if found_kiu:
        logger.info("Detectado GDS: KIU (heurística)")
        return _parse_kiu_ticket(plain_text, html_text)

    logger.warning("No se pudo determinar el GDS del boleto; retornando datos vacíos.")
    return {"error": "GDS no reconocido"}


# --- GENERACIÓN DE PDF ---

def generate_ticket(data: Dict[str, Any]) -> Tuple[bytes, str]:
    """
    Genera un PDF a partir de los datos parseados, seleccionando la plantilla correcta.
    """
    source_system = data.get('SOURCE_SYSTEM', 'KIU') # Default a KIU si no se especifica
    
    if source_system == 'SABRE':
        template_name = "tickets/ticket_template_sabre.html"
        # Mapeo de datos para la plantilla de Sabre
        context = {
            'pasajero': data.get('preparado_para', ''),
            'id_pasajero': data.get('numero_cliente', '-'),
            'codigo_reservacion': data.get('codigo_reservacion', ''),
            'numero_boleto': data.get('numero_boleto', ''),
            'fecha_emision': data.get('fecha_emision', ''),
            'aerolinea_emisora': data.get('aerolinea_emisora', ''),
            'numero_iata': data.get('numero_iata', '-'),
            'vuelos': data.get('vuelos', [])
        }
    else: # Default para KIU y otros
        template_name = "tickets/ticket_template_kiu.html"
        # Mapeo de datos para la plantilla de KIU
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
            'salidas': data.get('ItinerarioFinalLimpio') or data.get('ITINERARIO_DE_VUELO', ''),
        }

    # Configuración de Jinja2
    base_dir = os.path.dirname(os.path.abspath(__file__))
    template_dir = os.path.join(base_dir, 'templates', 'core')
    env = Environment(loader=FileSystemLoader(template_dir), autoescape=select_autoescape(['html', 'xml']))
    
    template = env.get_template(template_name)
    html_out = template.render(context)
    
    # Generación de PDF en memoria
    # Importar WeasyPrint al momento de generar el PDF para evitar fallos en entornos sin las dependencias nativas
    try:
        from weasyprint import HTML
    except Exception as e:
        raise RuntimeError("WeasyPrint no está disponible en el entorno. Instala weasyprint y sus dependencias nativas para generar PDFs. Error: {}".format(e))

    pdf_bytes = HTML(string=html_out, base_url=base_dir).write_pdf()
    
    # Nombre del archivo
    timestamp = dt.datetime.now().strftime("%Y%m%d%H%M%S")
    ticket_num_raw = data.get("numero_boleto") or data.get("NUMERO_DE_BOLETO", "SIN_TICKET")
    ticket_num_for_file = re.sub(r'[\\/*?:"<>|]', "", _clean_value(ticket_num_raw)).replace(" ", "_") or "SIN_TICKET"
    file_name = f"Boleto_{ticket_num_for_file}_{timestamp}.pdf" 
    
    return pdf_bytes, file_name
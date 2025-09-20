# Archivo: core/parsing_utils.py
# Contiene funciones auxiliares de parseo para ser reutilizadas por diferentes parsers de GDS.

import re
import logging
import datetime as dt
from datetime import timedelta
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

def _clean_value(value: Any) -> str:
    """Limpia un valor, convirtiéndolo a string y eliminando espacios sobrantes."""
    if value is None:
        return ''
    return str(value).strip()

def _parse_currency_amount(value: str) -> Tuple[Optional[str], Optional[Decimal]]:
    """Intenta separar moneda (3 letras) y monto a Decimal de una cadena."""
    if not value or value == 'No encontrado':
        return None, None
    txt = re.sub(r'\s+', ' ', value.strip())
    # Regex corregido para evitar 'multiple repeat' y manejar correctamente los decimales.
    m = re.match(r'^([A-Z]{3})\s+([0-9,.]+)$', txt)
    if not m:
        m = re.match(r'^([A-Z]{3})([0-9,.]+)$', txt)
    if m:
        currency = m.group(1)
        amount_raw = m.group(2).replace(',', '')
        try:
            amount = Decimal(amount_raw)
        except InvalidOperation:
            amount = None
        return currency, amount
    return None, None

def _extract_field(text: str, patterns: List[str], default: str = 'No encontrado') -> str:
    """Extrae un campo usando una lista de patrones regex."""
    for pattern in patterns:
        try:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                try:
                    return match.group(1).strip()
                except IndexError:
                    return match.group(0).strip()
        except re.error as e:
            logger.error(f"Error de Regex en el patrón '{pattern}': {e}")
            continue
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

def _formatear_fecha_dd_mm_yyyy(fecha_str: Optional[str]) -> str:
    """Convierte una fecha (ej: '08 may 25', '2025-05-08') a formato DD-MM-YYYY."""
    if not fecha_str:
        return ''
    
    month_map = {
        'ene': 'Jan', 'feb': 'Feb', 'mar': 'Mar', 'abr': 'Apr', 'may': 'May', 'jun': 'Jun',
        'jul': 'Jul', 'ago': 'Aug', 'sep': 'Sep', 'oct': 'Oct', 'nov': 'Nov', 'dic': 'Dec'
    }
    
    cleaned_date = fecha_str.strip().lower()
    for es, en in month_map.items():
        cleaned_date = cleaned_date.replace(es, en)

    formatos_probables = [
        '%d %b %y',  # 08 may 25
        '%d %b %Y',  # 08 May 2025
        '%Y-%m-%d',  # 2025-05-08
        '%d/%m/%y',
        '%d/%m/%Y',
    ]
    for fmt in formatos_probables:
        try:
            return dt.datetime.strptime(cleaned_date, fmt).strftime('%d-%m-%Y')
        except ValueError:
            continue
    return fecha_str

def _fecha_a_iso(fecha_str: str) -> Optional[str]:
    """Convierte cadena de fecha conocida a ISO (YYYY-MM-DD) si es posible."""
    if not fecha_str:
        return None
    original = fecha_str.strip()
    for fmt in ('%d-%m-%Y', '%d %b %y', '%d %b %Y', '%Y-%m-%d'):
        try:
            dt_obj = dt.datetime.strptime(original, fmt)
            return dt_obj.strftime('%Y-%m-%d')
        except ValueError:
            continue
    return None

def _inferir_fecha_llegada(fecha_salida: str, hora_salida: str, hora_llegada: str, fecha_llegada_existente: Optional[str]) -> str:
    """Devuelve fecha_llegada en DD-MM-YYYY: usa la existente; si no, asume mismo día o +1 si hora_llegada < hora_salida."""
    if fecha_llegada_existente:
        return _formatear_fecha_dd_mm_yyyy(fecha_llegada_existente)
    if not fecha_salida:
        return ''
    try:
        base = dt.datetime.strptime(_formatear_fecha_dd_mm_yyyy(fecha_salida), '%d-%m-%Y')
    except (ValueError, TypeError):
        return ''
    if hora_salida and hora_llegada:
        try:
            hs = dt.datetime.strptime(hora_salida, '%H:%M')
            hl = dt.datetime.strptime(hora_llegada, '%H:%M')
            if hl < hs:
                base = base + timedelta(days=1)
        except (ValueError, TypeError):
            pass
    return base.strftime('%d-%m-%Y')

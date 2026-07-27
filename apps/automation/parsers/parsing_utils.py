# Archivo: apps/automation/parsers/parsing_utils.py
# Contiene funciones auxiliares de parseo específicas para GDS.
# Importa utilidades centralizadas desde apps/common/utils cuando sea posible.

import datetime as dt
import logging
import re
from datetime import timedelta
from decimal import Decimal
from typing import Any

from apps.automation.parsers.normalization import GDS_MONTH_EN, GDS_SHORT_TO_NUM
from apps.common.utils import clean_currency

logger = logging.getLogger(__name__)


def _clean_value(value: Any) -> str:
    """Limpia un valor, convirtiéndolo a string y eliminando espacios sobrantes."""
    if value is None:
        return ""
    return str(value).strip()


def _parse_currency_amount(value: str) -> tuple[str | None, Decimal | None]:
    """Intenta separar moneda (3 letras) y monto a Decimal de una cadena."""
    if not value or value == "No encontrado":
        return None, None
    txt = re.sub(r"\s+", " ", value.strip())
    m = re.match(r"^([A-Z]{3})\s*(.+)$", txt)
    if m:
        currency = m.group(1)
        amount_raw = m.group(2)
        amount = clean_currency(amount_raw)
        return currency, amount
    return None, None


def _extract_field(text: str, patterns: list[str], default: str = "No encontrado") -> str:
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


def _extract_field_single_line(
    text: str, patterns: list[str], default: str = "No encontrado"
) -> str:
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


def _formatear_fecha_dd_mm_yyyy(fecha_str: str | None) -> str:
    """Convierte una fecha (ej: '08 may 25', '2025-05-08') a formato DD-MM-YYYY."""
    if not fecha_str:
        return ""

    cleaned = fecha_str.strip().lower()

    # 1. Verificar si ya es YYYY-MM-DD
    m_iso = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", cleaned)
    if m_iso:
        return f"{m_iso.group(3)}-{m_iso.group(2)}-{m_iso.group(1)}"

    # 2. Verificar si es DD/MM/YYYY o DD/MM/YY
    m_slash = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{2,4})$", cleaned)
    if m_slash:
        d, m, y = m_slash.group(1), m_slash.group(2), m_slash.group(3)
        if len(y) == 2:
            y = f"20{y}"
        return f"{int(d):02d}-{int(m):02d}-{y}"

    # 3. Verificar si es DD-MM-YYYY o DD-MM-YY
    m_dash = re.match(r"^(\d{1,2})-(\d{1,2})-(\d{2,4})$", cleaned)
    if m_dash:
        d, m, y = m_dash.group(1), m_dash.group(2), m_dash.group(3)
        if len(y) == 2:
            y = f"20{y}"
        return f"{int(d):02d}-{int(m):02d}-{y}"

    # P2-005: Mapas derivados de constantes centralizadas en normalization.py
    month_to_num = {k.lower(): f"{v:02d}" for k, v in GDS_SHORT_TO_NUM.items()}
    # Incluir también las abreviaciones de 3 letras inglesas por su nombre completo
    month_to_num.update({k.lower(): f"{v:02d}" for k, v in GDS_SHORT_TO_NUM.items() if len(k) == 3})

    # Manejar formatos como "13 Aug 25", "13 aug 2025", "13aug25", "13aug2025"
    m_word = re.match(r"^(\d{1,2})\s*([a-z]{3})\s*(\d{2,4})$", cleaned)
    if m_word:
        d = int(m_word.group(1))
        month_abbr = m_word.group(2)
        y = m_word.group(3)
        if month_abbr in month_to_num:
            m = month_to_num[month_abbr]
            if len(y) == 2:
                y = f"20{y}"
            return f"{d:02d}-{m}-{y}"

    # Fallback usando strptime con limpieza a inglés
    month_map = {k.lower(): v.title() for k, v in GDS_MONTH_EN.items()}
    cleaned_date = cleaned
    for es, en in month_map.items():
        cleaned_date = cleaned_date.replace(es, en)

    formatos_probables = [
        "%d %b %y",
        "%d %b %Y",
        "%d%b%y",
        "%d%b%Y",
        "%Y-%m-%d",
        "%d/%m/%y",
        "%d/%m/%Y",
    ]
    for fmt in formatos_probables:
        try:
            return dt.datetime.strptime(cleaned_date, fmt).strftime("%d-%m-%Y")
        except ValueError:
            continue
    return fecha_str


def _fecha_a_iso(fecha_str: str) -> str | None:
    """Convierte cadena de fecha conocida a ISO (YYYY-MM-DD) si es posible."""
    if not fecha_str:
        return None
    original = fecha_str.strip()

    # 1. Intentar parsear el formato DD-MM-YYYY directo primero
    m_dash = re.match(r"^(\d{2})-(\d{2})-(\d{4})$", original)
    if m_dash:
        return f"{m_dash.group(3)}-{m_dash.group(2)}-{m_dash.group(1)}"

    # Fallback
    for fmt in ("%d-%m-%Y", "%Y-%m-%d", "%d %b %y", "%d %b %Y"):
        try:
            dt_obj = dt.datetime.strptime(original, fmt)
            return dt_obj.strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def _inferir_fecha_llegada(
    fecha_salida: str, hora_salida: str, hora_llegada: str, fecha_llegada_existente: str | None
) -> str:
    """Devuelve fecha_llegada en DD-MM-YYYY: usa la existente; si no, asume mismo día o +1 si hora_llegada < hora_salida."""
    if fecha_llegada_existente:
        return _formatear_fecha_dd_mm_yyyy(fecha_llegada_existente)
    if not fecha_salida:
        return ""
    try:
        base = dt.datetime.strptime(_formatear_fecha_dd_mm_yyyy(fecha_salida), "%d-%m-%Y")
    except (ValueError, TypeError):
        return ""
    if hora_salida and hora_llegada:
        try:
            hs = dt.datetime.strptime(hora_salida, "%H:%M")
            hl = dt.datetime.strptime(hora_llegada, "%H:%M")
            if hl < hs:
                base = base + timedelta(days=1)
        except (ValueError, TypeError) as e:
            logger.warning(
                f"Error al inferir fecha de llegada para salida {fecha_salida} {hora_salida}: {e}"
            )
    return base.strftime("%d-%m-%Y")


def _parse_date_flexible(
    date_str: str, reference_date: dt.datetime | None = None, base_year: int = None
) -> str:
    """
    Parsea una fecha de vuelo (ej: 29JAN, 02FEB26) y la convierte a ISO (YYYY-MM-DD).
    Usa reference_date (fecha de emisión) para inferir el año correcto en fechas ambiguas (ej: Ene vs Dic).
    Si no hay reference_date, usa base_year.
    """
    if not date_str:
        return ""

    date_upper = date_str.upper().strip()

    from apps.automation.parsers.normalization import GDS_MONTH_EN as month_map_es

    for es, en in month_map_es.items():
        date_upper = date_upper.replace(es, en)

    try:
        # Caso 1: Tiene año 2 dígitos al final (Ej: 02FEB26)
        # Regex: \d{1,2}[A-Z]{3}\d{2}
        if re.match(r"^\d{1,2}[A-Z]{3}\d{2}$", date_upper):
            dt_obj = dt.datetime.strptime(date_upper, "%d%b%y")
            return dt_obj.strftime("%Y-%m-%d")

        # Caso 2: Tiene año 4 dígitos (Ej: 02FEB2026)
        if re.match(r"^\d{1,2}[A-Z]{3}\d{4}$", date_upper):
            dt_obj = dt.datetime.strptime(date_upper, "%d%b%Y")
            return dt_obj.strftime("%Y-%m-%d")

        # Caso 3: Sin año (Ej: 02FEB)
        if re.match(r"^\d{1,2}[A-Z]{3}$", date_upper):
            # Determinar año base
            year = base_year or dt.now().year
            if reference_date:
                year = reference_date.year

            # Intentar parsear con ese año
            dt_obj = dt.datetime.strptime(date_upper + str(year), "%d%b%Y")

            # Ajuste de año nuevo (Rollover):
            # Si tenemos ref_date (ej: Dic 2025) y el vuelo es "anterior" (ej: Ene 2025),
            # significa que es Ene el año siguiente (2026).
            if reference_date:
                # Si la fecha parseada es más de 10 meses ANTERIOR a la referencia, sumar 1 año
                # (Ej: Vuelo Ene 2025, Emision Dic 2025 -> Diff -11 meses -> Sumar año)
                # Si la fecha parseada es más de 10 meses POSTERIOR? (Ej: Vuelo Dic, Emision Ene -> ok)
                if (reference_date - dt_obj).days > 300:  # aprox 10 meses
                    dt_obj = dt_obj.replace(year=year + 1)
                # Tambien, si el vuelo es Ene 07 y emision Ene 08, es pasado? No, es posible.
                # Pero si es Ene y emision Dic, el año debe cambiar.
                elif (
                    dt_obj.month < reference_date.month
                    and (reference_date.month - dt_obj.month) > 6
                ):
                    dt_obj = dt_obj.replace(year=year + 1)

            return dt_obj.strftime("%Y-%m-%d")

        return date_str  # Si no matchea nada conocido

    except ValueError as e:
        logger.debug(f"No se pudo parsear fecha flexible '{date_str}': {e}")
        return date_str

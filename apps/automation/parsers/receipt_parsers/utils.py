"""
Utility functions for receipt parsers.
Extracted from web_receipt_parser.py to reduce duplication.
"""

import logging
import re
from decimal import Decimal, InvalidOperation

logger = logging.getLogger(__name__)


def clean_money(value_str: str) -> Decimal:
    """
    Limpia strings de moneda a Decimal.

    Soporta formatos:
    - 1,234.56 (US/UK)
    - 1.234,56 (Español/Venezuela)
    - 1234.56 (simple)
    - 1234,56 (simple europeo)

    Args:
        value_str: String con el valor monetario

    Returns:
        Decimal con el valor limpio, o Decimal("0.00") si falla
    """
    if not value_str:
        return Decimal("0.00")
    try:
        clean = re.sub(r"[^\d.,]", "", value_str)
        if not clean:
            return Decimal("0.00")

        if "," in clean and "." in clean:
            if clean.find(".") < clean.find(","):
                clean = clean.replace(".", "").replace(",", ".")
            else:
                clean = clean.replace(",", "")
        elif "," in clean:
            clean = clean.replace(",", ".")

        return Decimal(clean)
    except (InvalidOperation, ValueError):
        return Decimal("0.00")


def identify_airline(ticket_number: str) -> str:
    """
    Deduce la aerolínea basada en el prefijo del boleto (IATA 3-digits).

    Prefijos conocidos:
    - 052 -> ESTELAR
    - 742 -> AVIOR
    - 765 -> RUTACA

    Args:
        ticket_number: Número de boleto (13 dígitos)

    Returns:
        Nombre de la aerolínea
    """
    clean_tkt = re.sub(r"[^\d]", "", ticket_number)
    if clean_tkt.startswith("052"):
        return "AEROLINEAS ESTELAR LATINOAMERICA C.A."
    elif clean_tkt.startswith("742"):
        return "AVIOR AIRLINES C.A"
    elif clean_tkt.startswith("765"):
        return "RUTACA AIRLINES"
    return "AEROLINEA DESCONOCIDA"


def get_airline_data_from_db(
    airline_name: str, default_agent: str = "", default_address: str = ""
) -> dict:
    """
    Busca la aerolínea en Cliente o Proveedor para obtener dirección y agente.

    Prioridad: Cliente -> Proveedor -> Default Hardcoded.

    Args:
        airline_name: Nombre de la aerolínea a buscar
        default_agent: Agente por defecto si no se encuentra
        default_address: Dirección por defecto si no se encuentra

    Returns:
        Dict con 'agente' y 'direccion'
    """
    try:
        from apps.bookings.models import Proveedor
        from apps.crm.models import Cliente

        cliente = (
            Cliente.objects.filter(nombres__icontains=airline_name).first()
            or Cliente.objects.filter(apellidos__icontains=airline_name).first()
        )

        if cliente:
            logger.info(f"Datos de Aerolínea encontrados en Cliente: {cliente}")
            return {
                "agente": default_agent,
                "direccion": cliente.direccion or default_address,
            }

        proveedor = Proveedor.objects.filter(nombre__icontains=airline_name).first()
        if proveedor:
            logger.info(f"Datos de Aerolínea encontrados en Proveedor: {proveedor}")
            return {
                "agente": default_agent,
                "direccion": proveedor.direccion or default_address,
            }

    except Exception as e:
        logger.warning(f"No se pudo consultar DB para datos de aerolínea: {e}")

    return {"agente": default_agent, "direccion": default_address}


def parse_spanish_date(text: str) -> dict:
    """
    Extrae fecha en formato español del texto.

    Busca patrones como: "Lunes, 29 de Enero de 2026"

    Args:
        text: Texto donde buscar la fecha

    Returns:
        Dict con 'day', 'month', 'year', 'fecha_display', 'fecha_iso'
    """
    from datetime import datetime

    date_pattern = r"(?:Lunes|Martes|Miércoles|Miercoles|Jueves|Viernes|Sábado|Sabado|Domingo)\w*,\s*(\d{1,2})\s*de\s*(\w+)\s*de\s*(\d{4})"
    d_match = re.search(date_pattern, text, re.IGNORECASE)

    meses = {
        "enero": "01",
        "febrero": "02",
        "marzo": "03",
        "abril": "04",
        "mayo": "05",
        "junio": "06",
        "julio": "07",
        "agosto": "08",
        "septiembre": "09",
        "octubre": "10",
        "noviembre": "11",
        "diciembre": "12",
    }
    meses_abbr = {
        "enero": "ENE",
        "febrero": "FEB",
        "marzo": "MAR",
        "abril": "ABR",
        "mayo": "MAY",
        "junio": "JUN",
        "julio": "JUL",
        "agosto": "AGO",
        "septiembre": "SEP",
        "octubre": "OCT",
        "noviembre": "NOV",
        "diciembre": "DIC",
    }

    if d_match:
        day = d_match.group(1).zfill(2)
        month_str = d_match.group(2).lower()
        year = d_match.group(3)
    else:
        now = datetime.now()
        day = str(now.day).zfill(2)
        month_str = now.strftime("%B").lower()
        year = str(now.year)

    mes_num = meses.get(month_str, "01")
    mes_abbr = meses_abbr.get(month_str, "XXX").upper()
    year_short = year[-2:] if len(year) == 4 else year

    return {
        "day": day,
        "month_num": mes_num,
        "month_abbr": mes_abbr,
        "year": year,
        "year_short": year_short,
        "fecha_display": f"{day}{mes_abbr}{year_short}",
        "fecha_iso": f"{year}-{mes_num}-{day}",
    }


def format_money_ve(amount: Decimal) -> str:
    """
    Formatea un Decimal al formato monetario venezolano.

    Args:
        amount: Valor a formatear

    Returns:
        String formateado (ej: "1.234,56")
    """
    if not amount:
        return "0,00"

    str_amount = f"{amount:.2f}"
    integer_part, decimal_part = str_amount.split(".")

    integer_formatted = ""
    for i, digit in enumerate(reversed(integer_part)):
        if i > 0 and i % 3 == 0:
            integer_formatted = "." + integer_formatted
        integer_formatted = digit + integer_formatted

    return f"{integer_formatted},{decimal_part}"

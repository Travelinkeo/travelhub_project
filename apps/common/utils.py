import re
import logging
from decimal import Decimal, InvalidOperation

logger = logging.getLogger(__name__)

def clean_currency(value):
    """
    Limpia un string de moneda y lo convierte a Decimal de forma robusta.
    Maneja formatos: "$ 1.200,50", "1,200.50", "Bs. 100.000,00", "1500"
    """
    if value is None or value == "":
        return Decimal("0.00")
    
    if isinstance(value, (int, float)):
        return Decimal(str(value))
    
    if isinstance(value, Decimal):
        return value

    try:
        # 1. Eliminar cualquier carácter que no sea dígito, punto o coma
        # pero conservar el signo negativo si existe al inicio
        is_negative = value.strip().startswith('-')
        cleaned = re.sub(r'[^0-9,.]', '', value)
        
        if not cleaned:
            return Decimal("0.00")

        # 2. Normalización de separadores
        # Si hay ambos (punto y coma), el último suele ser el decimal
        if ',' in cleaned and '.' in cleaned:
            if cleaned.rfind('.') > cleaned.rfind(','):
                # Caso: 1,200.50 -> 1200.50
                cleaned = cleaned.replace(',', '')
            else:
                # Caso: 1.200,50 -> 1200.50
                cleaned = cleaned.replace('.', '').replace(',', '.')
        
        # Si solo hay coma, evaluamos si es decimal (ej: 1500,50) o miles (ej: 1,500)
        elif ',' in cleaned:
            parts = cleaned.split(',')
            if len(parts[-1]) == 2: # Muy probable decimal
                cleaned = cleaned.replace(',', '.')
            else:
                cleaned = cleaned.replace(',', '')
        
        # Si hay múltiples puntos (ej: 1.200.000), son separadores de miles
        elif cleaned.count('.') > 1:
            cleaned = cleaned.replace('.', '')

        result = Decimal(cleaned)
        return -result if is_negative else result

    except (InvalidOperation, ValueError, TypeError) as e:
        logger.warning(f"Error limpiando monto financiero '{value}': {e}")
        return Decimal("0.00")

def clean_json_string(text):
    """
    Limpia un string que contiene JSON, eliminando posibles bloques de código markdown.
    """
    if not text:
        return ""
    
    text = text.strip()
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        text = text.split("```")[1].split("```")[0]
    
    return text.strip()

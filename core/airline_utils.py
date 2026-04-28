# Archivo: core/airline_utils.py

import logging
from typing import Optional
from .models_catalogos import Aerolinea

logger = logging.getLogger(__name__)

def get_airline_name_by_code(codigo_iata: str) -> Optional[str]:
    """
    Obtiene el nombre de la aerolínea desde el catálogo usando el código IATA.
    
    Args:
        codigo_iata: Código IATA de 2 letras (ej: "AA", "AV", "LA")
    
    Returns:
        Nombre de la aerolínea o None si no se encuentra
    """
    if not codigo_iata or len(codigo_iata) != 2:
        return None
    
    try:
        aerolinea = Aerolinea.objects.filter(
            codigo_iata__iexact=codigo_iata.upper(),
            activa=True
        ).first()
        
        if aerolinea:
            logger.debug(f"Aerolínea encontrada: {codigo_iata} -> {aerolinea.nombre}")
            return aerolinea.nombre
        else:
            logger.warning(f"Aerolínea no encontrada para código: {codigo_iata}")
            return None
            
    except Exception as e:
        logger.error(f"Error al buscar aerolínea {codigo_iata}: {e}")
        return None

def extract_airline_code_from_flight(numero_vuelo: str) -> Optional[str]:
    """
    Extrae el código de aerolínea de un número de vuelo.
    
    Args:
        numero_vuelo: Número de vuelo completo (ej: "AA1234", "AV123")
    
    Returns:
        Código IATA de 2 letras o None si no se puede extraer
    """
    if not numero_vuelo:
        return None
    
    # Buscar patrón de 2 letras al inicio del número de vuelo
    import re
    match = re.match(r'^([A-Z]{2})', numero_vuelo.upper().strip())
    
    if match:
        return match.group(1)
    
    return None

def normalize_airline_name(raw_name: str, flight_number: str = None, ticket_number: str = None) -> str:
    """
    Normaliza el nombre de aerolínea usando el catálogo.
    Prioriza el código del número de vuelo sobre el texto del nombre.
    
    Args:
        raw_name: Nombre crudo extraído del boleto
        flight_number: Número de vuelo para extraer código IATA
        ticket_number: Número de boleto para extraer placa (ej: 057)
    
    Returns:
        Nombre normalizado de la aerolínea o el nombre original si no se encuentra
    """
    # Palabras comunes que NO son códigos IATA (evitar falsos positivos)
    EXCLUDED_WORDS = {
        'DE', 'LA', 'EL', 'EN', 'AL', 'OR', 'NO', 'SI', 'SE', 'ME', 'TE', 'LE',
        'UN', 'DO', 'TO', 'OF', 'IN', 'ON', 'AT', 'BY', 'IS', 'IT', 'AS', 'AN',
        'CA', 'SA', 'CO', 'US', 'AE', 'AR', 'AP', 'RP'  # Sufijos corporativos y agente emisor
    }
    
    # PRIORIDAD SUPERIOR: Búsqueda por Placa (Ticket Number Prefix)
    # Es la fuente más confiable (ambigüedad cero)
    if ticket_number:
        # Limpiar ticket number (ej: "134-1234567890" -> "134")
        clean_ticket = ''.join(filter(str.isdigit, str(ticket_number)))
        if len(clean_ticket) >= 3:
            prefix = clean_ticket[:3]
            try:
                aerolinea = Aerolinea.objects.filter(codigo_numerico=prefix).first()
                if aerolinea:
                    logger.info(f"Aerolínea identificada por placa {prefix}: {aerolinea.nombre}")
                    return aerolinea.nombre
            except Exception as e:
                logger.error(f"Error buscando aerolínea por placa {prefix}: {e}")

    # PRIORIDAD 0: Chequeo de texto directo (Para evitar confusiones AV vs AVIOR)
    # LISTA MAESTRA DE AEROLINEAS KIU (LEY)
    # Formato: TERMINO_BUSQUEDA: NOMBRE_NORMALIZADO
    KIU_AIRLINES_MASTER = {
        "RUTACA": "RUTAS AEREAS DE VENEZUELA", # 5R
        "PAWA": "PAWA DOMINICANA", # 7N
        "AIR PANAMA": "AIR PANAMA", # 7P
        "SATENA": "SATENA", # 9R
        "AVIOR": "AVIOR AIRLINES", # 9V
        "AEROCARIBE": "AEROCARIBE", # CV
        "AEROPOSTAL": "AEROPOSTAL ALAS DE VENEZUELA", # CW
        "SKY HIGH": "SKY HIGH AVIATION", # DO
        "ESTELAR": "AEROLINEAS ESTELAR", # ES
        "ALIANZA GLANCELOT": "ALIANZA GLANCELOT", # G0
        "GLOBAL APP": "GLOBAL AIRLINES", # G6 (Ajuste nombre comercial)
        "GLOBAL AIRLINES": "GLOBAL AIRLINES",
        "FLY THE WORLD": "FLY THE WORLD", # GI
        "RED AIR": "RED AIR", # L5
        "SASCA": "SASCA AIRLINES", # O3
        "PLUS ULTRA": "PLUS ULTRA", # PU
        "LASER": "LASER AIRLINES", # QL
        "SKY ATLANTIC": "SKY ATLANTIC TRAVEL", # T7
        "TURPIAL": "TURPIAL AIRLINES", # T9
        "CONVIASA": "CONVIASA", # V0
        "RUTAS AEREAS DE VENEZUELA": "RUTAS AEREAS DE VENEZUELA", # WW
        "AEROLINEAS ARGENTINAS": "AEROLINEAS ARGENTINAS",
        "AVIANCA": "AVIANCA",
        "TACA": "AVIANCA",
        "COPA": "COPA AIRLINES",
        "LATAM": "LATAM AIRLINES",
        "SATA": "SATA",
        "TURKISH": "TURKISH AIRLINES"
    }

    upper_name = raw_name.upper() if raw_name else ""
    
    # Busqueda directa en la lista maestra
    for key, normalized_name in KIU_AIRLINES_MASTER.items():
        if key in upper_name:
            return normalized_name

    # PRIORIDAD 1: Código del vuelo (más confiable)
    if flight_number:
        codigo = extract_airline_code_from_flight(flight_number)
        if codigo and codigo not in EXCLUDED_WORDS:
            nombre_catalogo = get_airline_name_by_code(codigo)
            if nombre_catalogo:
                logger.info(f"Aerolínea normalizada desde vuelo {flight_number}: {nombre_catalogo}")
                return nombre_catalogo
    
    # PRIORIDAD 2: Buscar códigos IATA al INICIO del nombre (más confiable que en medio)
    if raw_name:
        import re
        # Buscar código IATA al inicio del nombre (ej: "5R-RUTACA" -> "5R")
        match_inicio = re.match(r'^([A-Z0-9]{2})[-\s]', raw_name.upper())
        if match_inicio:
            codigo = match_inicio.group(1)
            if codigo not in EXCLUDED_WORDS:
                nombre_catalogo = get_airline_name_by_code(codigo)
                if nombre_catalogo:
                    logger.info(f"Aerolínea normalizada desde inicio del nombre: {nombre_catalogo}")
                    return nombre_catalogo
    
    # PRIORIDAD 3: Buscar códigos en el texto (menos confiable, solo si no hay otra opción)
    if raw_name and not flight_number and not ticket_number:
        import re
        codes = re.findall(r'\b([A-Z]{2})\b', raw_name.upper())
        for code in codes:
            if code in EXCLUDED_WORDS:
                continue
            
            nombre_catalogo = get_airline_name_by_code(code)
            if nombre_catalogo:
                logger.info(f"Aerolínea normalizada desde texto del nombre: {nombre_catalogo}")
                return nombre_catalogo
    
    # Si no se encuentra en el catálogo, devolver el nombre original limpio
    logger.debug(f"Aerolínea no normalizada, usando nombre original: {raw_name}")
    return raw_name if raw_name else "Aerolínea no identificada"

def validate_airline_numeric_code(ticket_number: str, airline_iata: str) -> bool:
    """
    Valida si el número de boleto corresponde a la aerolínea (IATA) indicada,
    basándose en el prefijo numérico (ej: Avianca=134).
    
    Args:
        ticket_number: Número de boleto (ej: "134-1234567890")
        airline_iata: Código IATA de la aerolínea (ej: "AV")
        
    Returns:
        True si coincide o si no hay datos para validar.
        False si hay una discrepancia clara (ej: Boleto empiza por 001 (AA) pero aerolínea es AV).
    """
    if not ticket_number or not airline_iata:
        return True # No se puede validar, asumimos válido para no bloquear
        
    # Limpiar número de boleto (quitar guiones y espacios)
    clean_ticket = ticket_number.replace('-', '').replace(' ', '').strip()
    
    if len(clean_ticket) < 3:
        return True
        
    prefix = clean_ticket[:3]
    
    try:
        aerolinea = Aerolinea.objects.filter(codigo_iata__iexact=airline_iata).first()
        if not aerolinea or not aerolinea.numeric_code:
            return True # No tenemos el código numérico registrado, pasamos
            
        # FIX: El campo en el modelo es codigo_numerico, no numeric_code
        if aerolinea.codigo_numerico == prefix:
            return True
        else:
            logger.warning(f"⚠️ Discrepancia Validación Numérica: Boleto {ticket_number} (Prefijo {prefix}) != {airline_iata} (Código {aerolinea.codigo_numerico})")
            return False
            
    except Exception as e:
        logger.error(f"Error validando código numérico: {e}")
        return True
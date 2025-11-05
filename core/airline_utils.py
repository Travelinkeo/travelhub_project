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

def normalize_airline_name(raw_name: str, flight_number: str = None) -> str:
    """
    Normaliza el nombre de aerolínea usando el catálogo.
    Prioriza el código del número de vuelo sobre el texto del nombre.
    
    Args:
        raw_name: Nombre crudo extraído del boleto
        flight_number: Número de vuelo para extraer código IATA
    
    Returns:
        Nombre normalizado de la aerolínea o el nombre original si no se encuentra
    """
    # Palabras comunes que NO son códigos IATA (evitar falsos positivos)
    EXCLUDED_WORDS = {
        'DE', 'LA', 'EL', 'EN', 'AL', 'OR', 'NO', 'SI', 'SE', 'ME', 'TE', 'LE',
        'UN', 'DO', 'TO', 'OF', 'IN', 'ON', 'AT', 'BY', 'IS', 'IT', 'AS', 'AN',
        'CA', 'SA', 'CO', 'US', 'AE', 'AR', 'AP', 'RP'  # Sufijos corporativos y agente emisor
    }
    
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
    if raw_name and not flight_number:
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
"""
Adaptador para mantener compatibilidad con código legacy.
Permite usar los nuevos parsers sin romper el código existente.
"""

import logging
from typing import Dict, Any

from .registry import registry
from .sabre_parser import SabreParser
from .amadeus_parser import AmadeusParser
from .kiu_parser import KIUParser
from .copa_parser import CopaParser
from .wingo_parser import WingoParser
from .tk_connect_parser import TKConnectParser

logger = logging.getLogger(__name__)

# Registrar parsers al importar el módulo
_parsers_registered = False

def _register_parsers():
    """Registra todos los parsers disponibles"""
    global _parsers_registered
    if _parsers_registered:
        return
    
    registry.register(SabreParser())
    registry.register(AmadeusParser())
    registry.register(KIUParser())
    registry.register(CopaParser())
    registry.register(WingoParser())
    registry.register(TKConnectParser())
    
    _parsers_registered = True
    logger.info("Todos los parsers refactorizados registrados (6/6)")


def parse_ticket_with_new_parsers(text: str, html_text: str = "") -> Dict[str, Any]:
    """
    Función adaptadora que usa los nuevos parsers pero retorna
    el formato esperado por el código legacy.
    
    Args:
        text: Texto plano del boleto
        html_text: HTML del boleto (opcional)
        
    Returns:
        Diccionario en formato legacy
    """
    _register_parsers()
    
    parser = registry.find_parser(text)
    if not parser:
        return {"error": "No se encontró parser compatible"}
    
    try:
        parsed_data = parser.parse(text, html_text)
        return parsed_data.to_dict()
    except Exception as e:
        logger.exception(f"Error al parsear con {parser.__class__.__name__}")
        return {"error": f"Error en parseo: {str(e)}"}

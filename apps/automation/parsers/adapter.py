"""
Adaptador para mantener compatibilidad con código legacy.
Permite usar los nuevos parsers sin romper el código existente.
"""

import logging
from typing import Any

from .kiu_parser import KIUParser
from .legacy.amadeus_parser import AmadeusParser
from .legacy.copa_parser import CopaParser
from .legacy.sabre_parser import SabreParser
from .legacy.tk_connect_parser import TKConnectParser
from .legacy.travelport_parser import TravelportParser
from .legacy.web_receipt_parser import WebReceiptParser
from .legacy.wingo_parser import WingoParser
from .registry import registry

logger = logging.getLogger(__name__)

# Registrar parsers al importar el módulo
_parsers_registered = False


def _register_parsers():
    """Registra todos los parsers disponibles"""
    global _parsers_registered
    if _parsers_registered:
        return

    registry.register(KIUParser())
    registry.register(WebReceiptParser())
    registry.register(CopaParser())
    registry.register(WingoParser())
    registry.register(TKConnectParser())
    registry.register(SabreParser())
    registry.register(AmadeusParser())
    registry.register(TravelportParser())

    _parsers_registered = True
    logger.info("Todos los parsers refactorizados registrados (8/8)")


def parse_ticket_with_new_parsers(text: str, html_text: str = "") -> dict[str, Any]:
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
        if not parsed_data:
            return {"error": "Parser returned no data"}

        # 🚨 CRÍTICO | Validación con Pydantic (ResultadoParseoSchema)
        # Garantiza que el output del parser se valide estrictamente contra el JSON Schema unificado
        try:
            parsed_data.to_pydantic()
            logger.info(
                f"✅ [Pydantic Validation] Exito al validar la salida de {parser.__class__.__name__} contra ResultadoParseoSchema."
            )
        except Exception as e_val:
            logger.warning(
                f"⚠️ [Pydantic Validation] La salida de {parser.__class__.__name__} no pudo validarse contra ResultadoParseoSchema: {e_val}"
            )

        return parsed_data.to_dict()
    except Exception as e:
        logger.exception(f"Error al parsear con {parser.__class__.__name__}")
        return {"error": f"Error en parseo: {str(e)}"}

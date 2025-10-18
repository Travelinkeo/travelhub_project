"""
Registro centralizado de parsers de boletos.
Permite registrar y buscar parsers dinámicamente.
"""

from typing import List, Optional
import logging

from .base_parser import BaseTicketParser

logger = logging.getLogger(__name__)


class ParserRegistry:
    """Registro centralizado de parsers de boletos"""
    
    def __init__(self):
        self._parsers: List[BaseTicketParser] = []
    
    def register(self, parser: BaseTicketParser) -> None:
        """
        Registra un nuevo parser.
        
        Args:
            parser: Instancia del parser a registrar
        """
        if not isinstance(parser, BaseTicketParser):
            raise TypeError(f"Parser debe ser instancia de BaseTicketParser, recibido: {type(parser)}")
        
        self._parsers.append(parser)
        logger.info(f"Parser registrado: {parser.__class__.__name__}")
    
    def find_parser(self, text: str) -> Optional[BaseTicketParser]:
        """
        Encuentra el parser apropiado para el texto dado.
        
        Args:
            text: Texto del boleto a analizar
            
        Returns:
            Parser que puede procesar el texto o None si no se encuentra
        """
        for parser in self._parsers:
            try:
                if parser.can_parse(text):
                    logger.info(f"Parser encontrado: {parser.__class__.__name__}")
                    return parser
            except Exception as e:
                logger.warning(f"Error al verificar parser {parser.__class__.__name__}: {e}")
                continue
        
        logger.warning("No se encontró parser compatible para el texto")
        return None
    
    def get_all_parsers(self) -> List[BaseTicketParser]:
        """Retorna lista de todos los parsers registrados"""
        return self._parsers.copy()
    
    def clear(self) -> None:
        """Limpia todos los parsers registrados"""
        self._parsers.clear()
        logger.info("Registro de parsers limpiado")


# Instancia global del registro
registry = ParserRegistry()

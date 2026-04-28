"""
Módulo de parsers de boletos refactorizado.
Proporciona una interfaz común para todos los parsers de GDS.
"""

from .base_parser import BaseTicketParser, ParsedTicketData
from .registry import ParserRegistry

__all__ = ['BaseTicketParser', 'ParsedTicketData', 'ParserRegistry']

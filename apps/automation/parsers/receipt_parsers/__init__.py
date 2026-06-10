"""
Receipt Parsers - Parsers especializados para recibos web de aerolíneas venezolanas.

Módulo modular para parsear recibos HTML/PDF de:
- Avior Airlines
- Estelar Airlines
- Rutaca Airlines

Uso:
    from apps.automation.parsers.receipt_parsers import MultiParsedTicketData
    from apps.automation.parsers.receipt_parsers.utils import clean_money, identify_airline
"""

from .data_classes import MultiParsedTicketData
from .utils import clean_money, get_airline_data_from_db, identify_airline

__all__ = [
    "MultiParsedTicketData",
    "clean_money",
    "identify_airline",
    "get_airline_data_from_db",
]

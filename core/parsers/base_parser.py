"""
Clase base para todos los parsers de boletos.
Proporciona métodos comunes y define la interfaz que deben implementar todos los parsers.
"""

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Dict, Any, Optional, List, Tuple
import logging

logger = logging.getLogger(__name__)


@dataclass
class ParsedTicketData:
    """Estructura normalizada de datos de boleto"""
    source_system: str
    pnr: str
    ticket_number: Optional[str]
    passenger_name: str
    issue_date: str
    flights: List[Dict[str, Any]] = field(default_factory=list)
    fares: Dict[str, Any] = field(default_factory=dict)
    agency: Dict[str, Any] = field(default_factory=dict)
    raw_data: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario para compatibilidad con código legacy"""
        return {
            'SOURCE_SYSTEM': self.source_system,
            'pnr': self.pnr,
            'numero_boleto': self.ticket_number,
            'pasajero': {'nombre_completo': self.passenger_name},
            'fecha_emision': self.issue_date,
            'vuelos': self.flights,
            'tarifas': self.fares,
            'agencia': self.agency,
            **self.raw_data
        }


class BaseTicketParser(ABC):
    """Clase base abstracta para todos los parsers de boletos"""
    
    @abstractmethod
    def can_parse(self, text: str) -> bool:
        """
        Determina si este parser puede procesar el texto dado.
        
        Args:
            text: Texto del boleto a analizar
            
        Returns:
            True si este parser puede procesar el texto
        """
        pass
    
    @abstractmethod
    def parse(self, text: str, html_text: str = "") -> ParsedTicketData:
        """
        Parsea el texto y retorna datos normalizados.
        
        Args:
            text: Texto plano del boleto
            html_text: HTML del boleto (opcional)
            
        Returns:
            ParsedTicketData con los datos extraídos
        """
        pass
    
    # Métodos comunes compartidos por todos los parsers
    
    def extract_currency_amount(self, text: str) -> Tuple[Optional[str], Optional[Decimal]]:
        """
        Extrae moneda y monto de un texto.
        
        Args:
            text: Texto que contiene moneda y monto (ej: "USD 1,234.56")
            
        Returns:
            Tupla (moneda, monto) o (None, None) si no se encuentra
        """
        if not text or text == 'No encontrado':
            return None, None
        
        match = re.search(r'([A-Z]{3})\s*([0-9,.]+)', text)
        if match:
            currency = match.group(1)
            amount_str = match.group(2).replace(',', '')
            try:
                amount = Decimal(amount_str)
                return currency, amount
            except (InvalidOperation, ValueError):
                logger.warning(f"No se pudo convertir monto: {amount_str}")
                return currency, None
        
        return None, None
    
    def normalize_date(self, date_str: str, format_hint: str = None) -> Optional[str]:
        """
        Normaliza una fecha a formato ISO (YYYY-MM-DD).
        
        Args:
            date_str: Fecha en formato variable
            format_hint: Pista del formato esperado
            
        Returns:
            Fecha en formato ISO o None si no se puede parsear
        """
        if not date_str or date_str == 'No encontrado':
            return None
        
        # Importar utilidades de parsing existentes
        from core.parsing_utils import _formatear_fecha_dd_mm_yyyy, _fecha_a_iso
        
        formatted = _formatear_fecha_dd_mm_yyyy(date_str)
        iso_date = _fecha_a_iso(formatted) or _fecha_a_iso(date_str)
        
        return iso_date
    
    def clean_text(self, text: str) -> str:
        """
        Limpia texto eliminando espacios extras y caracteres especiales.
        
        Args:
            text: Texto a limpiar
            
        Returns:
            Texto limpio
        """
        if not text:
            return ""
        
        # Eliminar espacios múltiples
        text = re.sub(r'\s+', ' ', text)
        # Eliminar espacios al inicio y final
        text = text.strip()
        
        return text
    
    def extract_field(self, text: str, patterns: List[str], default: str = 'No encontrado') -> str:
        """
        Extrae un campo usando múltiples patrones regex.
        
        Args:
            text: Texto donde buscar
            patterns: Lista de patrones regex a probar
            default: Valor por defecto si no se encuentra
            
        Returns:
            Valor extraído o default
        """
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                return self.clean_text(match.group(1))
        
        return default
    
    def normalize_airline_name(self, raw_name: str, flight_code: str = None) -> str:
        """
        Normaliza el nombre de aerolínea usando utilidades existentes.
        
        Args:
            raw_name: Nombre crudo de la aerolínea
            flight_code: Código de vuelo para ayudar en la normalización
            
        Returns:
            Nombre normalizado
        """
        from core.airline_utils import normalize_airline_name
        return normalize_airline_name(raw_name, flight_code)

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
    """
    🚨 CRÍTICO | 🧠 IA / GOD MODE
    Estructura de Datos de Transferencia (DTO) que define la "Única Verdad" (Single Source of Truth) del ecosistema.
    
    ¿Por qué?: Los GDS (Sabre, KIU, Amadeus) tienen salidas radicalmente diferentes (HTML roto vs Plaintext).
    Tanto nuestras Expresiones Regulares heredadas (legacy) como Gemini (IA Parser) DEBEN mapear su resultado 
    final a este Dataclass. Si alteras esto, crasheará la generación de Facturas, PDFs y la tabla `core_venta`.
    """
    source_system: str
    pnr: str
    ticket_number: Optional[str]
    passenger_name: str
    issue_date: str
    passenger_document: Optional[str] = None
    flights: List[Dict[str, Any]] = field(default_factory=list)
    fares: Dict[str, Any] = field(default_factory=dict)
    agency: Dict[str, Any] = field(default_factory=dict)
    es_remision: bool = False
    raw_data: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        🚨 CRÍTICO
        Exporta el DTO a un diccionario plano estandarizado. 
        Sigue estrictamente el mapeo "BIBLIA DEL PARSEO" requerido por los templates Jinja2 del front-end 
        (ej. 'NOMBRE DEL PASAJERO', 'TARIFA_IMPORTE') y por los workers de Celery al registrar la Venta.
        
        Returns:
            Dict[str, Any]: El diccionario masivo con alias retro-compatibles para el dashboard de ERP.
        """
        
        # ... (lógica existente) ...
        # [OMITIDO PARA BREVEDAD, el resto del to_dict se mantiene igual pero incluyendo es_remision]
        # Re-implementar el to_dict completo para asegurar integridad
        
        # 1. Aerolínea del primer vuelo (o del raw_data)
        airline_name = self.raw_data.get('airline_name')
        if not airline_name and self.flights:
            airline_name = self.flights[0].get('aerolinea')
            
        # 2. Solo Nombre Pasajero (Regla de Memoria)
        from core.ticket_parser import _get_solo_nombre_pasajero
        solo_nombre = self.raw_data.get('solo_nombre_pasajero') or _get_solo_nombre_pasajero(self.passenger_name)
        
        # 3. Solo Código Reserva (Limpieza C1/)
        solo_pnr = self.pnr
        if solo_pnr and '/' in solo_pnr:
            solo_pnr = solo_pnr.split('/')[-1]
            
        # 4. Agente Emisor (ID Único)
        agente_id = self.agency.get('iata') or self.agency.get('numero_iata') or self.agency.get('name')
        if agente_id:
            # Regla: solo el ID/Número
            match = re.search(r'([A-Z0-9]{3,})', str(agente_id))
            if match: agente_id = match.group(1)

        # 5. Estructura de Finanzas
        tarifa = self.fares.get('fare_amount')
        moneda = self.fares.get('fare_currency') or self.fares.get('total_currency')
        t_str = f"{moneda} {tarifa}" if tarifa and moneda else str(tarifa) if tarifa else "No encontrado"
        
        total = self.fares.get('total_amount')
        total_str = f"{moneda} {total}" if total and moneda else str(total) if total else "No encontrado"
        
        impuestos = self.fares.get('tax_amount')
        if not impuestos and total and tarifa:
            try: impuestos = f"{float(total) - float(tarifa):.2f}"
            except: impuestos = "0.00"

        return {
            'SOURCE_SYSTEM': self.source_system,
            # LLAVES MANDATORIAS (BIBLIA DEL PARSEO)
            'NOMBRE DEL PASAJERO': self.passenger_name,
            'CODIGO IDENTIFICACION': self.passenger_document or self.raw_data.get('FOID') or 'No encontrado',
            'SOLO NOMBRE PASAJERO': solo_nombre,
            'NUMERO DE BOLETO': self.ticket_number,
            'FECHA DE EMISION': self.issue_date,
            'AGENTE EMISOR': agente_id,
            'CODIGO RESERVA': self.pnr,
            'SOLO CODIGO RESERVA': solo_pnr,
            'NOMBRE AEROLINEA': airline_name or 'No encontrado',
            'DIRECCION AEROLINEA': self.raw_data.get('direccion_aerolinea') or 'No encontrado',
            'vuelos': self.flights,
            'TARIFA': t_str,
            'IMPUESTOS': impuestos,
            'TOTAL': total_str,
            'es_remision': self.es_remision, # NUEVO CAMPO
            
            # Aliases para compatibilidad con código antiguo/templates
            'pnr': self.pnr,
            'ticket_number': self.ticket_number,
            'passenger_name': self.passenger_name,
            'fecha_emision': self.issue_date,
            'TARIFA_IMPORTE': tarifa,
            'TOTAL_IMPORTE': total,
            'TARIFA_MONEDA': moneda,
            'TOTAL_MONEDA': moneda,
            'agencia': self.agency
        }


class BaseTicketParser(ABC):
    """
    Clase base abstracta (Contrato/Interfaz) para todos los motores de extracción del sistema.
    
    ¿Por qué?: Implementamos el patrón arquitectónico Strategy. El orquestador itera sobre todos los
    parsers subclases (SabreParser, KIUParser, AIParser) y ejecuta `can_parse(...)` para saber
    quién debe hacerse cargo del archivo subido. Promueve extrema escalabilidad para nuevos proveedores.
    """
    
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
            raw_amount = match.group(2)
            
            # Determinar si la coma o el punto es el separador decimal
            last_comma = raw_amount.rfind(',')
            last_dot = raw_amount.rfind('.')
            
            if last_comma > last_dot and (len(raw_amount) - last_comma == 3):
                # La coma es decimal (ej: 1.234,56 o 492,25)
                amount_str = raw_amount.replace('.', '').replace(',', '.')
            else:
                # El punto es decimal (ej: 1,234.56 o 492.25)
                amount_str = raw_amount.replace(',', '')
                
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
    
    def normalize_airline_name(self, raw_name: str, flight_code: str = None, ticket_number: str = None) -> str:
        """
        Normaliza el nombre de aerolínea usando utilidades existentes.
        
        Args:
            raw_name: Nombre crudo de la aerolínea
            flight_code: Código de vuelo para ayudar en la normalización
            ticket_number: Número de boleto para extraer placa/prefijo
            
        Returns:
            Nombre normalizado
        """
        from core.airline_utils import normalize_airline_name
        return normalize_airline_name(raw_name, flight_code, ticket_number=ticket_number)
    def extract_passenger_name_robust(self, text: str) -> str:
        """
        Extrae el nombre completo del pasajero aislando etiquetas HTML y ruido basura.
        
        Args:
            text (str): Texto plano o HTML crudo empaquetado del correo (.eml).
            
        Returns:
            str: Nombre extraído (ej. "PEREZ/JUANA") o 'No encontrado'.
            
        # ¿Por qué es robusto?: El GDS suele encadenar el nombre de pasajero con el documento (FOID/RIF)
        # o inyectar etiquetas SPAN en medio. Si eso se cuela a la DB o Stripe (Pasarela), rechazan 
        # las tarjetas por discrepancia de titular. Este método previene dicho desastre financiero.
        """
        # Limpiar HTML para la búsqueda de nombres
        clean_text = re.sub(r'<[^>]+>', ' ', text)
        clean_text = clean_text.replace('&nbsp;', ' ')
        
        # 1. Prioridad: Búsqueda por palabras clave explícitas (KIU/Sabre/Web)
        patterns = [
            r'NAME/NOMBRE\s*[:\s]*([A-ZÁÉÍÓÚÑ/ (),.-]{3,})',
            r'NAME:\s*([A-ZÁÉÍÓÚÑ/ (),.-]{3,})',
            r'NOMBRE DEL PASAJERO\s*[:\s]*([A-ZÁÉÍÓÚÑ/ (),.-]{3,})',
            r'PASAJERO\s*[:\s]*([A-ZÁÉÍÓÚÑ/ (),.-]{3,})',
            r'PASJ\s*[:\s]*([A-ZÁÉÍÓÚÑ/ (),.-]{3,})',
        ]
        
        raw_name = self.extract_field(clean_text, patterns)
        
        # 2. Estrategia 2: GDS Priority (APELLIDO/NOMBRE) si no hubo palabra clave
        if raw_name == 'No encontrado' or len(raw_name) < 4:
            blacklist = [
                'DATE/FECHA', 'FECHA/EMISION', 'NAME/NOMBRE', 'AGENT/AGENTE', 'FROM/TO', 'DESDE/HACIA', 
                'TELEFONO', 'PHONE', 'MAIL', 'CORREO', 'DOCUMENTO', 'ADDRESS/DIRECCION', 
                'TICKET NUMBER/NRO DE BOLETO', 'NO REEMBOLSABLE/NO ENDOSABLE', 'NON END/NON REF',
                'AIR FARE/TARIFA', 'TAX/IMPUESTOS', 'FORM OF PAYMENT/FORMA DE PAGO', 'PAGO',
                'ISSUING AIRLINE', 'LINEA AEREA EMISORA', 'EMISORA', 'AIRLINE', 'DIRECCION',
                'FORMA DE PAGO', 'TARIFA', 'IMPUESTOS', 'NUMERO DE BOLETO', 'PASSENGER NAME',
                'RESERVATION CODE', 'CODIGO DE RESERVA', 'CODIGO DE RESERVACION', 'ELECTRONIC',
                'RECORD LOCATOR', 'BOOKING REFERENCE', 'TICKET NUMBER', 'ISSUE AGENT', 'EMITIDO'
            ]
            
            # Buscar en el texto limpio (sin tags)
            matches = re.finditer(r'\b([A-Z]{2,}(?: [A-Z]+)*/[A-Z]{2,}(?: [A-Z]+)*)\b', clean_text)
            for match in matches:
                candidate = match.group(1).strip()
                if len(candidate) > 5 and not re.search(r'\d', candidate):
                    if not any(bad in candidate.upper() for bad in blacklist):
                         raw_name = candidate
                         break

        if raw_name == 'No encontrado':
            return 'No encontrado'

        return self.clean_passenger_name(raw_name)

    def clean_passenger_name(self, name: str) -> str:
        """
        Filtra sufijos y títulos de cortesía (MR, MRS, CHD) inyectados por la aerolínea.
        
        Args:
            name (str): Nombre crudo pre-extraído.
            
        Returns:
            str: Nombre sanitizado sin sufijos ni prefijos corporativos.
            
        # 🚨 CRÍTICO: Este método prohíbe explícitamente barrer PNRs, IDs, o FOIDs que vengan colisionados.
        # En vuelos chárter, las aerolíneas exigen que la cédula y el GDS permanezcan juntos. 
        # Separar eso aquí causaría un NO SHOW en aeropuerto.
        """
        if not name or name == 'No encontrado':
            return name

        # 1. Asegurar limpieza de cualquier tag residual (HTML)
        name = re.sub(r'<[^>]+>', '', name)
        name = name.replace('&nbsp;', ' ').strip()

        # 2. Eliminación de títulos y sufijos (MR, MS, MRS, CHD, INF) 
        # Solo si hay un separador '/' (Estilo GDS/KIU)
        if '/' in name:
            name = re.sub(r'\s*\b(MR|MS|MRS|CHD|INF)\b\s*$', '', name, flags=re.IGNORECASE).strip()
        
        # 3. Limpieza de caracteres residuales
        name = name.rstrip(':/.- ').strip()
        
        return name

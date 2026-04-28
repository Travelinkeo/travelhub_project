import re
import logging
from typing import List, Dict, Any, Optional
from core.parsing_utils import _formatear_fecha_dd_mm_yyyy

logger = logging.getLogger(__name__)

class ConsoleParser:
    """
    Parser especializado para interpretar texto crudo (raw) copiado directamente
    de consolas GDS (Sabre, Amadeus, KIU, etc.).
    
    A diferencia del TicketParser, este no espera números de boleto, 
    impuestos detallados o cabeceras de correo electrónico.
    """

    def parse(self, text: str) -> Dict[str, Any]:
        """
        Intenta detectar el formato y extraer segmentos de vuelo.
        Retorna un diccionario con la estructura estándar:
        {
            'source_system': 'SABRE'|'KIU'|'AMADEUS'|'UNKNOWN',
            'vuelos': [...],
            'raw_text': text
        }
        """
        text_upper = text.upper()
        
        # 1. Detectar KIU Raw
        # Regex 1: 1 5R300 S 30NOV SU CCSPMV HK1 0800 0840 (Clase separada)
        # Relaxed: Allow space between Airline/FlightNum, optional class spacing
        kiu_pattern_1 = r'^\s*\d+\s+[A-Z0-9]{2}\s*\d+\s+[A-Z]\s+\d{2}[A-Z]{3}'
        # Regex 2: 1  V01014T 01DEC MO CCSPMV SS1  0600 0650 (Clase pegada)
        kiu_pattern_2 = r'^\s*\d+\s+[A-Z0-9]{2}\d+[A-Z]?\s+\d{2}[A-Z]{3}'
        
        if re.search(kiu_pattern_1, text, re.MULTILINE) or re.search(kiu_pattern_2, text, re.MULTILINE):
            logger.info("ConsoleParser: Detectado formato KIU Raw")
            result = self._parse_kiu_raw(text)
            result['time_limit'] = self._extract_time_limit(text)
            return result

        # 2. Detectar Sabre Raw
        # Regex: 1 AV4816K 03DEC...
        sabre_pattern = r'^\s*\d+\s+[A-Z0-9]{2}\s*\d+[A-Z]?\s+\d{2}[A-Z]{3}'
        if re.search(sabre_pattern, text, re.MULTILINE):
            logger.info("ConsoleParser: Detectado formato Sabre Raw")
            # Nota: Sabre y KIU (patrón 2) son muy similares. 
            # Si KIU no parsea nada, podríamos intentar Sabre, pero por ahora asumimos KIU si coincide.
            result = self._parse_sabre_raw(text)
            result['time_limit'] = self._extract_time_limit(text)
            return result

        # 3. Detectar Amadeus Raw (Placeholder - patrones comunes)
        # 1  IB6500 J 10DEC 7 MADBOG HK1       1210 1635   346 E 0
        amadeus_pattern = r'^\s*\d+\s+[A-Z0-9]{2}\d+\s+[A-Z]\s+\d{2}[A-Z]{3}'
        # (Similar a KIU/Sabre, a veces hay que diferenciar por contexto)
        
        return {
            'source_system': 'UNKNOWN',
            'vuelos': [],
            'error': 'No se pudo detectar un formato de consola conocido.'
        }

    def _parse_kiu_raw(self, text: str) -> Dict[str, Any]:
        flights = []
        lines = text.splitlines()
        
        # Pattern 1: Clase separada (1 5R300 S 30NOV...)
        pattern_1 = r'^\s*\d+\s+([A-Z0-9]{2})\s*(\d+)\s+([A-Z])\s+(\d{2}[A-Z]{3})\s+[A-Z]{2}\s+([A-Z]{3})([A-Z]{3})\s+[A-Z0-9]+\s+(\d{4})\s+(\d{4})'
        
        # Pattern 2: Clase pegada (1 V01014T 01DEC...)
        # Grupos: 1:Aerolinea, 2:Vuelo, 3:Clase(Opcional), 4:Fecha, 5:Origen, 6:Destino, 7:Salida, 8:Llegada
        pattern_2 = r'^\s*\d+\s+([A-Z0-9]{2})\s*(\d+)([A-Z])?\s+(\d{2}[A-Z]{3})\s+[A-Z]{2}\s+([A-Z]{3})([A-Z]{3})\s+[A-Z0-9]+\s+(\d{4})\s+(\d{4})'
        
        for line in lines:
            # Intentar Pattern 1
            match = re.search(pattern_1, line)
            if match:
                flights.append({
                    "aerolinea": match.group(1),
                    "numero_vuelo": match.group(2),
                    "clase": match.group(3),
                    "fecha_salida": match.group(4),
                    "origen": match.group(5),
                    "destino": match.group(6),
                    "hora_salida": f"{match.group(7)[:2]}:{match.group(7)[2:]}",
                    "hora_llegada": f"{match.group(8)[:2]}:{match.group(8)[2:]}",
                })
                continue
                
            # Intentar Pattern 2
            match = re.search(pattern_2, line)
            if match:
                flights.append({
                    "aerolinea": match.group(1),
                    "numero_vuelo": match.group(2),
                    "clase": match.group(3) if match.group(3) else "",
                    "fecha_salida": match.group(4),
                    "origen": match.group(5),
                    "destino": match.group(6),
                    "hora_salida": f"{match.group(7)[:2]}:{match.group(7)[2:]}",
                    "hora_llegada": f"{match.group(8)[:2]}:{match.group(8)[2:]}",
                })
        
        return {
            'source_system': 'KIU',
            'vuelos': flights,
            'ItinerarioFinalLimpio': text # Mantener compatibilidad con traductor
        }

    def _parse_sabre_raw(self, text: str) -> Dict[str, Any]:
        flights = []
        lines = text.splitlines()
        # Regex flexible para Sabre: 1 AV 123 Y 10OCT 2 BOGMIA HK1 1000 1400
        # O: 1 AV4816K 03DEC...
        
        # Intento 1: Estructura compacta (AV4816K)
        pattern_compact = r'^\s*\d+\s+([A-Z0-9]{2})\s*(\d+[A-Z]?)\s+(\d{2}[A-Z]{3})\s+\d\s+([A-Z]{3})([A-Z]{3})[\s\*]+[A-Z0-9]+\s+(\d{4})\s+(\d{4})'
        
        # Intento 2: Estructura espaciada (AV 123)
        pattern_spaced = r'^\s*\d+\s+([A-Z0-9]{2})\s+(\d+)\s+([A-Z])\s+(\d{2}[A-Z]{3})\s+\d\s+([A-Z]{3})([A-Z]{3})\s+[A-Z0-9]+\s+(\d{4})\s+(\d{4})'

        for line in lines:
            # Probar compact
            match = re.search(pattern_compact, line)
            if match:
                flights.append({
                    "aerolinea": match.group(1),
                    "numero_vuelo": match.group(2),
                    "fecha_salida": match.group(3),
                    "origen": match.group(4),
                    "destino": match.group(5),
                    "hora_salida": f"{match.group(6)[:2]}:{match.group(6)[2:]}",
                    "hora_llegada": f"{match.group(7)[:2]}:{match.group(7)[2:]}",
                })
                continue

            # Probar spaced
            match = re.search(pattern_spaced, line)
            if match:
                flights.append({
                    "aerolinea": match.group(1),
                    "numero_vuelo": match.group(2),
                    "clase": match.group(3),
                    "fecha_salida": match.group(4),
                    "origen": match.group(5),
                    "destino": match.group(6),
                    "hora_salida": f"{match.group(7)[:2]}:{match.group(7)[2:]}",
                    "hora_llegada": f"{match.group(8)[:2]}:{match.group(8)[2:]}",
                })

        return {
            'source_system': 'SABRE',
            'vuelos': flights
        }

    def _extract_time_limit(self, text: str) -> Optional[str]:
        """
        Busca patrones de Tiempo Límite en el texto.
        Retorna el string encontrado (ej: "15JAN 12:00") o None.
        """
        # Patrones comunes
        patterns = [
            r'TKT BY\s+([0-9]{2}[A-Z]{3}(?:\s+[0-9]{4})?)',  # TKT BY 15JAN [2024]
            r'7T-([0-9]{2}[A-Z]{3})',                         # 7T-15JAN (Sabre)
            r'TIME LIMIT\s+([0-9]{2}[A-Z]{3})',               # TIME LIMIT 15JAN
            r'TL\s+([0-9]{2}[A-Z]{3})',                       # TL 15JAN
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0).upper() # Retorna todo el match ej "TKT BY 15JAN"
        
        return None

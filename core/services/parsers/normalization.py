# -*- coding: utf-8 -*-
import logging
import json
from decimal import Decimal
from datetime import date, datetime

logger = logging.getLogger(__name__)

class DataNormalizationService:
    """
    🎯 Responsabilidad: Normalizar datos extraídos por diversos motores (Regex/IA) a un esquema unificado.
    """

    @staticmethod
    def normalize_ticket_data(data):
        """Aplica alias y limpieza de campos para compatibilidad con el motor financiero."""
        if not isinstance(data, dict):
            return data

        # 1. Aliasing de campos comunes
        mappings = {
            'pnr': ['codigo_reserva', 'localizador', 'CODIGO_RESERVA'],
            'passenger_name': ['nombre_pasajero', 'NOMBRE_DEL_PASAJERO', 'nombre_completo', 'passenger name'],
            'ticket_number': ['numero_boleto', 'NUMERO_DE_BOLETO'],
            'issue_date': ['FECHA_DE_EMISION', 'fecha_emision'],
            'issuing_airline': ['NOMBRE_AEROLINEA', 'nombre_aerolinea'],
            'passenger_document': ['CODIGO_IDENTIFICACION', 'codigo_identificación', 'foid'],
            'fare_amount': ['tarifa', 'TARIFA_IMPORTE'],
            'total_amount': ['total', 'TOTAL', 'TOTAL_IMPORTE'],
            'total_currency': ['moneda', 'TOTAL_MONEDA', 'currency']
        }

        normalized = data.copy()
        for target, sources in mappings.items():
            if target not in normalized or not normalized[target]:
                for source in sources:
                    if source in normalized and normalized[source]:
                        normalized[target] = normalized[source]
                        break
        
        # 2. Procesamiento de Itinerario
        if 'itinerario' in normalized or 'flights' in normalized or 'segmentos' in normalized:
            raw_itinerary = normalized.get('itinerario') or normalized.get('flights') or normalized.get('segmentos') or []
            normalized['segmentos'] = DataNormalizationService._normalize_itinerary(raw_itinerary)
            # Para compatibilidad con legacy
            normalized['ItinerarioFinalLimpio'] = json.dumps(raw_itinerary)

        return DataNormalizationService.sanitize_for_json(normalized)

    @staticmethod
    def _normalize_itinerary(raw_itinerary):
        segmentos = []
        for tramo in raw_itinerary:
            if not isinstance(tramo, dict): continue
            
            # Soporte para estructura anidada (Gemini) vs plana (Regex)
            dep = tramo.get('departure', {}) if isinstance(tramo.get('departure'), dict) else {}
            arr = tramo.get('arrival', {}) if isinstance(tramo.get('arrival'), dict) else {}
            det = tramo.get('details', {}) if isinstance(tramo.get('details'), dict) else {}

            segmento = {
                'aerolinea': tramo.get('airline') or tramo.get('aerolinea'),
                'vuelo': tramo.get('flightNumber') or tramo.get('numero_vuelo') or tramo.get('vuelo'),
                'origen': dep.get('location') or tramo.get('origen'),
                'destino': arr.get('location') or tramo.get('destino'),
                'fecha_salida': dep.get('date') or tramo.get('fecha_salida') or tramo.get('date'),
                'hora_salida': dep.get('time') or tramo.get('hora_salida'),
                'fecha_llegada': arr.get('date') or tramo.get('fecha_llegada'),
                'hora_llegada': arr.get('time') or tramo.get('hora_llegada'),
                'clase': det.get('cabin') or tramo.get('clase') or tramo.get('cabina') or 'Y',
                'localizador_aerolinea': det.get('airlineReservationCode') or tramo.get('localizador_aerolinea')
            }
            segmentos.append(segmento)
        return segmentos

    @staticmethod
    def sanitize_for_json(data):
        if isinstance(data, dict):
            return {k: DataNormalizationService.sanitize_for_json(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [DataNormalizationService.sanitize_for_json(v) for v in data]
        elif isinstance(data, (date, datetime)):
            return data.isoformat()
        elif isinstance(data, Decimal):
            return str(data)
        return data

    @staticmethod
    def safe_decimal(val):
        if not val: return Decimal("0.00")
        try:
            s = str(val).upper().replace('USD','').replace('EUR','').replace('BS','').replace('VES','').strip()
            import re
            match = re.search(r'[\d,.]+', s)
            if not match: return Decimal("0.00")
            num_str = match.group(0)
            
            # Lógica para comas vs puntos (internacional)
            if ',' in num_str and '.' in num_str:
                if num_str.find('.') < num_str.find(','):
                    num_str = num_str.replace('.', '').replace(',', '.')
                else:
                    num_str = num_str.replace(',', '')
            elif ',' in num_str:
                num_str = num_str.replace(',', '.')
            return Decimal(num_str)
        except:
            return Decimal("0.00")

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
        # 🛡️ FIX SEGURIDAD: Si data es un string (JSON), lo parseamos
        d = data
        if isinstance(d, str):
            try: d = json.loads(d)
            except: d = {}
            
        if not isinstance(d, dict):
            return d or {}
        
        data = d # Trabajamos con el dict parseado

        # 1. Aliasing de campos comunes
        mappings = {
            'pnr': ['codigo_reserva', 'localizador', 'CODIGO_RESERVA'],
            'passenger_name': ['nombre_pasajero', 'NOMBRE_DEL_PASAJERO', 'nombre_completo', 'passenger name'],
            'ticket_number': ['numero_boleto', 'NUMERO_DE_BOLETO'],
            'issue_date': ['FECHA_DE_EMISION', 'fecha_emision'],
            'issuing_airline': ['NOMBRE_AEROLINEA', 'nombre_aerolinea', 'aerolinea_emisora', 'airline'],
            'passenger_document': ['CODIGO_IDENTIFICACION', 'codigo_identificación', 'foid'],
            'fare_amount': ['tarifa', 'TARIFA_IMPORTE'],
            'total_amount': ['total', 'TOTAL', 'TOTAL_IMPORTE'],
            'total_currency': ['moneda', 'TOTAL_MONEDA', 'currency'],
            'airline_pnr': ['pnr_aerolinea', 'CODIGO_RESERVA_AEROLINEA', 'airline_reservation_code']
        }

        normalized = data.copy()
        for target, sources in mappings.items():
            if target not in normalized or not normalized[target]:
                for source in sources:
                    if source in normalized and normalized[source]:
                        normalized[target] = normalized[source]
                        break
        
        # 1.1 Normalización específica de nombre de pasajero (Hola, [Nombre])
        if 'passenger_name' in normalized and '/' in normalized['passenger_name']:
            raw_name = normalized['passenger_name']
            try:
                # GDS Standard: APELLIDOS/NOMBRES MR
                parts = raw_name.split('/')
                if len(parts) > 1:
                    last_names = parts[0].strip()
                    # Limpiamos títulos comunes (MR, MRS, MS, MSTR, MISS)
                    import re
                    first_names_raw = parts[1].strip()
                    first_names = re.sub(r'\s+(MR|MRS|MS|MSTR|MISS|M|F)$', '', first_names_raw, flags=re.IGNORECASE)
                    
                    normalized['first_name'] = first_names
                    normalized['last_name'] = last_names
                    normalized['solo_nombre_pasajero'] = first_names.split(' ')[0] # El primer nombre para el saludo
                    # Re-armamos un nombre más amigable para humanos
                    normalized['human_name'] = f"{first_names} {last_names}"
            except Exception as e:
                logger.error(f"Error normalizando nombre {raw_name}: {e}")
        
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
        from core.services.catalog_service import CatalogNormalizationService
        
        for tramo in raw_itinerary:
            if not isinstance(tramo, dict): continue
            
            # Soporte para estructura anidada (Gemini) vs plana (Regex)
            dep = tramo.get('departure', {}) if isinstance(tramo.get('departure'), dict) else {}
            arr = tramo.get('arrival', {}) if isinstance(tramo.get('arrival'), dict) else {}
            det = tramo.get('details', {}) if isinstance(tramo.get('details'), dict) else {}

            vuelo_num = tramo.get('flightNumber') or tramo.get('numero_vuelo') or tramo.get('vuelo')
            
            # Normalización de tiempos
            h_salida = DataNormalizationService._normalize_time(dep.get('time') or tramo.get('hora_salida'))
            h_llegada = DataNormalizationService._normalize_time(arr.get('time') or tramo.get('hora_llegada'))
            
            # --- 🏙️ NORMALIZACIÓN POR CATÁLOGO IATA (DETERMINÍSTICO) ---
            origen_raw = dep.get('location') or tramo.get('origen')
            iata_origen = tramo.get('codigo_iata_origen') or (origen_raw if len(str(origen_raw)) == 3 else None)
            
            destino_raw = arr.get('location') or tramo.get('destino')
            iata_destino = tramo.get('codigo_iata_destino') or (destino_raw if len(str(destino_raw)) == 3 else None)
            
            # Resolver nombres vía catálogo si tenemos IATA
            ciudad_origen_obj = CatalogNormalizationService.get_or_create_ciudad_by_iata(iata_origen) if iata_origen else None
            ciudad_destino_obj = CatalogNormalizationService.get_or_create_ciudad_by_iata(iata_destino) if iata_destino else None
            
            segmento = {
                'aerolinea': tramo.get('airline') or tramo.get('aerolinea'),
                'vuelo': vuelo_num,
                'numero_vuelo': vuelo_num,
                'origen': ciudad_origen_obj.nombre if ciudad_origen_obj else origen_raw,
                'codigo_iata_origen': iata_origen,
                'destino': ciudad_destino_obj.nombre if ciudad_destino_obj else destino_raw,
                'codigo_iata_destino': iata_destino,
                'fecha_salida': dep.get('date') or tramo.get('fecha_salida') or tramo.get('date'),
                'hora_salida': h_salida,
                'fecha_llegada': arr.get('date') or tramo.get('fecha_llegada'),
                'hora_llegada': h_llegada,
                'clase': det.get('cabin') or tramo.get('clase') or tramo.get('cabina') or 'Y',
                'localizador_aerolinea': det.get('airlineReservationCode') or tramo.get('localizador_aerolinea') or tramo.get('airline_pnr') or tramo.get('pnr_aerolinea')
            }
            segmentos.append(segmento)
        return segmentos

    @staticmethod
    def _normalize_time(time_str):
        """Normaliza horas a formato 24h HH:mm"""
        if not time_str: return None
        s = str(time_str).strip().upper()
        
        # 1. Quitar segundos si existen (17:00:00 -> 17:00)
        s = s.split(':')[0] + ':' + s.split(':')[1] if len(s.split(':')) > 2 else s
        
        # 2. Conversión AM/PM
        if 'AM' in s or 'PM' in s:
            try:
                # Limpiar ruidos
                s_clean = s.replace('AM',' AM').replace('PM',' PM').replace('  ',' ')
                from datetime import datetime
                dt = datetime.strptime(s_clean, '%I:%M %p')
                return dt.strftime('%H:%M')
            except: pass
            
        # 3. Formato GDS (1721 -> 17:21)
        if len(s) == 4 and s.isdigit():
            return f"{s[:2]}:{s[2:]}"
            
        return s

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

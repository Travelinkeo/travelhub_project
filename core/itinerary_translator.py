# Archivo: core/itinerary_translator.py

import re
import json
import logging
import traceback
from typing import Dict, List, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class ItineraryTranslator:
    """Traductor de itinerarios aéreos usando el parser central."""
    
    CUSTOM_LOGOS = {
        'ES': 'https://upload.wikimedia.org/wikipedia/commons/1/11/Logo_Aerolineas_Estelar.png',
    }
    
    def __init__(self):
        self.airlines = self._load_airlines_catalog()
        self.airports = self._load_airports_catalog()
    
    def _load_airlines_catalog(self) -> Dict[str, str]:
        """Carga el catálogo de aerolíneas desde JSON y BD."""
        airlines = {}
        try:
            # 1. Cargar desde JSON (prioridad base)
            airlines_file = Path(__file__).parent / "data" / "airlines.json"
            if airlines_file.exists():
                with open(airlines_file, 'r', encoding='utf-8') as f:
                    airlines_data = json.load(f)
                    for airline in airlines_data:
                        airlines[airline['code']] = airline['name']
            
            # 2. Actualizar/Sobrescribir con BD (prioridad alta)
            from .models_catalogos import Aerolinea
            for airline in Aerolinea.objects.filter(activa=True):
                if airline.codigo_iata:
                    airlines[airline.codigo_iata] = airline.nombre
                    
            return airlines
        except Exception as e:
            logger.error(f"Error cargando catálogo de aerolíneas: {e}")
            return airlines

    def _load_airports_catalog(self) -> Dict[str, str]:
        """Carga el catálogo de aeropuertos desde archivo JSON."""
        try:
            airports_file = Path(__file__).parent / "data" / "airports.json"
            if airports_file.exists():
                with open(airports_file, 'r', encoding='utf-8') as f:
                    airports_data = json.load(f)
                    return {airport['code']: airport['name'] for airport in airports_data}
            else:
                return self._get_basic_airports()
        except Exception as e:
            logger.error(f"Error cargando catálogo de aeropuertos: {e}")
            return self._get_basic_airports()
    
    def _get_basic_airports(self) -> Dict[str, str]:
        """Catálogo básico de aeropuertos más comunes."""
        return {
            'CCS': 'Caracas', 'BOG': 'Bogotá', 'MIA': 'Miami', 'MAD': 'Madrid',
            'BCN': 'Barcelona', 'LIM': 'Lima', 'SCL': 'Santiago', 'GYE': 'Guayaquil',
            'UIO': 'Quito', 'PTY': 'Panamá', 'SJO': 'San José', 'LAX': 'Los Angeles',
            'JFK': 'Nueva York', 'CDG': 'París', 'LHR': 'Londres', 'FCO': 'Roma'
        }
    
    def _get_airline_logo_url(self, iata_code: str) -> str:
        """Obtiene la URL del logo de la aerolínea desde Travelpayouts."""
        if not iata_code or len(iata_code) != 2:
            return ""
            
        # Check custom logos first
        if iata_code in self.CUSTOM_LOGOS:
            return self.CUSTOM_LOGOS[iata_code]
            
        return f"https://pics.avs.io/200/200/{iata_code}.png"

    def translate_itinerary(self, itinerary: str, gds_system: str = 'SABRE') -> Dict[str, Any]:
        """
        Traduce el itinerario usando ConsoleParser.
        Retorna un diccionario:
        {
            'html': '...código html para visualizar...',
            'structured_data': [...lista de vuelos...],
            'error': '...mensaje si hubo error...'
        }
        """
        from core.parsers.console_parser import ConsoleParser
        
        result = {
            'html': '',
            'structured_data': [],
            'error': None
        }

        if not itinerary.strip():
            result['html'] = '<div class="error">Por favor, ingrese un itinerario válido.</div>'
            result['error'] = 'Itinerario vacío'
            return result
        
        try:
            # Usar el parser de consola
            parser = ConsoleParser()
            data = parser.parse(itinerary)
            
            if 'error' in data:
                # Fallback opcional: Intentar con el parser de tickets por si acaso pegaron un boleto completo
                from core.ticket_parser import extract_data_from_text
                logger.info("ConsoleParser falló, intentando con TicketParser como fallback...")
                ticket_data = extract_data_from_text(itinerary)
                if 'error' not in ticket_data:
                    data = ticket_data
                else:
                    result['html'] = f'<div class="error">{data["error"]}</div>'
                    result['error'] = data['error']
                    return result
            
            output = []
            structured_flights = []
            
            # Alerta de Tiempo Límite
            time_limit = data.get('time_limit')
            if time_limit:
                output.append(f'''
                <div class="mb-4 p-4 bg-orange-50 border-l-4 border-orange-500 rounded-r shadow-sm">
                    <div class="flex items-center">
                        <div class="flex-shrink-0">
                            <i class="fas fa-history text-orange-500 text-xl"></i>
                        </div>
                        <div class="ml-3">
                            <p class="text-sm font-bold text-orange-700">Tiempo Límite Detectado</p>
                            <p class="text-sm text-orange-600">Este itinerario vence: <span class="font-mono bg-orange-100 px-1 rounded">{time_limit}</span></p>
                        </div>
                    </div>
                </div>
                ''')
            
            # Caso 1: Estructura de vuelos estandarizada (Sabre, Amadeus, Copa, etc.)
            if 'vuelos' in data and data['vuelos']:
                for vuelo in data['vuelos']:
                    aerolinea = vuelo.get('aerolinea', 'XX')
                    # Intentar extraer código IATA si el nombre es largo
                    iata_code = 'XX'
                    if len(aerolinea) == 2:
                        iata_code = aerolinea
                    else:
                        num_vuelo = vuelo.get('numero_vuelo', '')
                        if num_vuelo and len(num_vuelo) > 2:
                            iata_code = num_vuelo[:2]
                    
                    # AUMENTO DE TAMAÑO DE LOGO: 64px -> 80px para mayor impacto visual
                    if len(aerolinea) == 2:
                        iata_code = aerolinea
                    
                    # Resolver nombre completo de la aerolínea
                    nombre_aerolinea = self.airlines.get(iata_code, aerolinea)
                        
                    logo_url = self._get_airline_logo_url(iata_code)
                    logo_html = f'<img src="{logo_url}" alt="{iata_code}" class="w-16 h-16 mr-4 object-contain">' if logo_url else ''
                    
                    origen = vuelo.get('origen', '???')
                    if isinstance(origen, dict):
                        origen = origen.get('ciudad', '???')
                        
                    destino = vuelo.get('destino', '???')
                    if isinstance(destino, dict):
                        destino = destino.get('ciudad', '???')
                        
                    origen_nombre = self.airports.get(origen, origen)
                    destino_nombre = self.airports.get(destino, destino)
                    
                    fecha = vuelo.get('fecha_salida', 'Fecha desc.')
                    hora_sal = vuelo.get('hora_salida', '--:--')
                    hora_lleg = vuelo.get('hora_llegada', '--:--')
                    
                    # Agregar a datos estructurados
                    structured_flights.append({
                        'type': 'flight',
                        'airline_code': iata_code,
                        'airline_name': nombre_aerolinea,
                        'flight_number': vuelo.get('numero_vuelo', ''),
                        'origin': origen,
                        'origin_name': origen_nombre,
                        'destination': destino,
                        'destination_name': destino_nombre,
                        'date': fecha,
                        'departure_time': hora_sal,
                        'arrival_time': hora_lleg
                    })
                    
                    output.append(f'''
                    <div class="flight-result flex items-center p-4 border-b border-gray-100 hover:bg-gray-50 transition-colors duration-200">
                        {logo_html}
                        <div class="flex-1">
                            <div class="flex items-center justify-between mb-2">
                                <span class="font-bold text-lg text-gray-800">{nombre_aerolinea} <span class="text-gray-500 text-base font-normal">{vuelo.get('numero_vuelo', '')}</span></span>
                                <span class="bg-blue-100 text-blue-800 text-xs font-semibold px-2.5 py-0.5 rounded">{iata_code}</span>
                            </div>
                            <div class="flex items-center text-sm text-gray-700 mb-1">
                                <span class="font-semibold mr-2">{fecha}</span>
                                <span class="mx-2 text-gray-400">|</span>
                                <span>{hora_sal} <span class="text-gray-400">➔</span> {hora_lleg}</span>
                            </div>
                            <div class="flex items-center text-xs text-gray-500">
                                <span class="truncate" title="{origen_nombre}">{origen_nombre} ({origen})</span>
                                <span class="mx-2">✈️</span>
                                <span class="truncate" title="{destino_nombre}">{destino_nombre} ({destino})</span>
                            </div>
                        </div>
                    </div>
                    ''')
            
            # Caso 2: KIU (ItinerarioFinalLimpio string)
            elif 'ItinerarioFinalLimpio' in data:
                lines = data['ItinerarioFinalLimpio'].split('\n')
                for line in lines:
                    match = re.search(r'^\s*\d+\s+([A-Z0-9]{2})\s*([0-9]+|[A-Z0-9]+)', line)
                    
                    logo_html = ''
                    airline_name = 'Aerolínea'
                    iata_code = 'XX'
                    flight_num = ''
                    
                    enriched_line = line
                    
                    if match:
                        iata_code = match.group(1)
                        flight_num = match.group(2)
                        airline_name = self.airlines.get(iata_code, iata_code)
                        logo_url = self._get_airline_logo_url(iata_code)
                        logo_html = f'<img src="{logo_url}" alt="{iata_code}" class="airline-logo" style="width: 80px; height: 80px; object-fit: contain; margin-right: 15px; background-color: white; padding: 5px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">'
                        
                        # Datos estructurados (parciales para KIU raw)
                        structured_flights.append({
                            'type': 'flight_raw_kiu',
                            'airline_code': iata_code,
                            'flight_number': flight_num,
                            'raw_line': line
                        })
                    
                    words = re.findall(r'\b[A-Z]{3}\b', line)
                    for word in words:
                        if word in self.airports:
                            enriched_line = enriched_line.replace(word, f"<b>{self.airports[word]} ({word})</b>")

                    output.append(f'''
                    <div class="flight-result-kiu p-4 border-b border-gray-100 font-mono text-sm flex items-center hover:bg-gray-50 transition-colors duration-200">
                        {logo_html}
                        <div class="flex-1">
                            <div class="font-bold text-lg text-gray-800 mb-1">{airline_name} {flight_num}</div>
                            <div class="text-gray-600 bg-gray-50 p-2 rounded border border-gray-200">{enriched_line}</div>
                        </div>
                    </div>
                    ''')
            
            else:
                result['html'] = '<div class="warning p-4 bg-yellow-50 text-yellow-700 rounded-md">Se detectaron datos pero no se pudo estructurar el itinerario.</div>'
                return result
                
            result['html'] = '\n'.join(output)
            result['structured_data'] = structured_flights
            return result
            
        except Exception as e:
            logger.error(f"Error traduciendo itinerario: {e}")
            logger.error(traceback.format_exc())
            result['html'] = '<div class="error p-4 bg-red-50 text-red-700 rounded-md">Error proceso interno al traducir.</div>'
            result['error'] = str(e)
            return result

class TicketCalculator:
    """Calculadora de precios de boletos."""
    
    @staticmethod
    def calculate_ticket_price(tarifa: float, fee_consolidador: float, fee_interno: float, porcentaje: float) -> Dict[str, Any]:
        """
        Calc    11111111111111111111322W222eto incluyendo IGTF (3%).
        Fórmula: (Tarifa + Fee Consolid. + Fee Interno) + % Ganancia + IGTF(3% del total)
        """
        try:
            suma_base = tarifa + fee_consolidador + fee_interno
            monto_porcentaje = suma_base * (porcentaje / 100)
            subtotal = suma_base + monto_porcentaje
            
            # IGTF (Impuesto a Grandes Transacciones Financieras - 3%)
            # Se asume que aplica al monto total en divisas
            igtf = subtotal * 0.03
            
            precio_final = subtotal + igtf
            
            return {
                'tarifa': tarifa,
                'fee_consolidador': fee_consolidador,
                'fee_interno': fee_interno,
                'suma_base': suma_base,
                'porcentaje': porcentaje,
                'monto_porcentaje': monto_porcentaje,
                'subtotal': subtotal,
                'igtf': igtf,
                'precio_final': precio_final,
                'desglose': f"Subtotal: ${subtotal:.2f} + IGTF (3%): ${igtf:.2f} = Total: ${precio_final:.2f}"
            }
        except Exception as e:
            logger.error(f"Error calculando precio de boleto: {e}")
            return {'error': str(e)}
# Archivo: core/itinerary_translator.py

import re
import json
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class ItineraryTranslator:
    """Traductor de itinerarios aéreos para diferentes GDS."""
    
    def __init__(self):
        self.airlines = self._load_airlines_catalog()
        self.airports = self._load_airports_catalog()
    
    def _load_airlines_catalog(self) -> Dict[str, str]:
        """Carga el catálogo de aerolíneas desde la base de datos."""
        try:
            from .models_catalogos import Aerolinea
            airlines = {}
            for airline in Aerolinea.objects.filter(activa=True):
                airlines[airline.codigo_iata] = airline.nombre
            return airlines
        except Exception as e:
            logger.error(f"Error cargando catálogo de aerolíneas: {e}")
            return {}
    
    def _load_airports_catalog(self) -> Dict[str, str]:
        """Carga el catálogo de aeropuertos desde archivo JSON."""
        try:
            airports_file = Path(__file__).parent / "data" / "airports.json"
            if airports_file.exists():
                with open(airports_file, 'r', encoding='utf-8') as f:
                    airports_data = json.load(f)
                    return {airport['code']: airport['name'] for airport in airports_data}
            else:
                logger.warning("Archivo de aeropuertos no encontrado, usando catálogo básico")
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
    
    def _format_date(self, date_str: str) -> str:
        """Formatea fecha de formato GDS a español."""
        months = {
            'JAN': 'enero', 'FEB': 'febrero', 'MAR': 'marzo', 'APR': 'abril',
            'MAY': 'mayo', 'JUN': 'junio', 'JUL': 'julio', 'AUG': 'agosto',
            'SEP': 'septiembre', 'OCT': 'octubre', 'NOV': 'noviembre', 'DEC': 'diciembre'
        }
        day = date_str[:2]
        month_code = date_str[2:5].upper()
        return f"{day} de {months.get(month_code, month_code)}"
    
    def _format_time(self, time_str: str) -> str:
        """Formatea hora de formato GDS."""
        return re.sub(r'(\d{2})(\d{2})(\+\d)?', r'\1:\2', time_str)
    
    def translate_sabre_itinerary(self, itinerary: str) -> str:
        """Traduce itinerario de formato SABRE."""
        flights = [line.strip() for line in itinerary.split('\n') if line.strip()]
        output = []
        
        for flight in flights:
            match = re.match(
                r'^\s*(\d+)\s*([A-Z0-9]{2})\s*(\d+\s*[A-Z]*)\s+(\d{2}[A-Z]{3})\s+\w\s+(\w{3})(\w{3})\W.*?\s+(\d{4})\s+(\d{4})\s+(\d{2}[A-Z]{3})?.*',
                flight
            )
            
            if not match:
                output.append(f'<div class="error">Error: Formato incorrecto en "{flight}"</div>')
                continue
            
            airline_code = match[2]
            flight_number = match[3].strip()
            departure_date = self._format_date(match[4])
            origin_code = match[5]
            dest_code = match[6]
            departure_time = self._format_time(match[7])
            arrival_time = self._format_time(match[8])
            arrival_date = self._format_date(match[9]) if match[9] else departure_date
            
            airline_name = self.airlines.get(airline_code, f"Código desconocido ({airline_code})")
            origin_name = self.airports.get(origin_code, origin_code)
            dest_name = self.airports.get(dest_code, dest_code)
            
            arrival_offset = " (día siguiente)" if match[9] and match[9] != match[4] else ""
            
            output.append(f'''
            <div class="flight-result">
                <strong>Vuelo {airline_code} {flight_number}</strong><br>
                <strong>Aerolínea:</strong> {airline_name}<br>
                <strong>Fecha:</strong> {departure_date}<br>
                <strong>Horario:</strong> {departure_time} → {arrival_time}{arrival_offset}<br>
                <strong>Ruta:</strong> {origin_name} → {dest_name}
            </div>
            ''')
        
        return '\n'.join(output)
    
    def translate_amadeus_itinerary(self, itinerary: str) -> str:
        """Traduce itinerario de formato Amadeus."""
        flights = [line.strip() for line in itinerary.split('\n') if line.strip()]
        output = []
        
        for flight in flights:
            match = re.match(
                r'^\s*(\d+)\s*([A-Z]{2})\s*(\d+[A-Z]*)\s+([A-Z])\s+([A-Z0-9]{5})\s+\w\s+(\w{3})(\w{3})\s+\S+(?:\s+\d+)?\s+(\d{4})\s+(\d{4})(?:\+(\d))?.*',
                flight
            )
            
            if not match:
                output.append(f'<div class="error">Error: Formato incorrecto en "{flight}"</div>')
                continue
            
            airline_code = match[2]
            flight_number = match[3]
            departure_date = self._format_date(match[5])
            origin_code = match[6]
            dest_code = match[7]
            departure_time = self._format_time(match[8])
            arrival_time = self._format_time(match[9])
            has_plus_one = match[10]
            
            airline_name = self.airlines.get(airline_code, f"Código desconocido ({airline_code})")
            origin_name = self.airports.get(origin_code, origin_code)
            dest_name = self.airports.get(dest_code, dest_code)
            
            arrival_offset = " (día siguiente)" if has_plus_one else ""
            
            output.append(f'''
            <div class="flight-result">
                <strong>Vuelo {airline_code} {flight_number}</strong><br>
                <strong>Aerolínea:</strong> {airline_name}<br>
                <strong>Fecha:</strong> {departure_date}<br>
                <strong>Horario:</strong> {departure_time} → {arrival_time}{arrival_offset}<br>
                <strong>Ruta:</strong> {origin_name} → {dest_name}
            </div>
            ''')
        
        return '\n'.join(output)
    
    def translate_kiu_itinerary(self, itinerary: str) -> str:
        """Traduce itinerario de formato KIU."""
        flights = [line.strip() for line in itinerary.split('\n') if line.strip()]
        output = []
        
        for flight in flights:
            match = re.match(
                r'^\s*(\d+)\s+([A-Z0-9]{2})\s*(\d+\s*[A-Z]*)\s+(\d{2}[A-Z]{3})\s+\w{2}\s+(\w{3})(\w{3})\s+.*?\s+(\d{4})\s+(\d{4})(\d{2}[A-Z]{3})?.*',
                flight
            )
            
            if not match:
                output.append(f'<div class="error">Error: Formato incorrecto en "{flight}"</div>')
                continue
            
            airline_code = match[2].strip()
            flight_number = match[3].replace(' ', '')
            departure_date = self._format_date(match[4])
            origin_code = match[5]
            dest_code = match[6]
            departure_time = self._format_time(match[7])
            arrival_time = self._format_time(match[8])
            arrival_date = self._format_date(match[9]) if match[9] else departure_date
            
            airline_name = self.airlines.get(airline_code, f"Código desconocido ({airline_code})")
            origin_name = self.airports.get(origin_code, origin_code)
            dest_name = self.airports.get(dest_code, dest_code)
            
            arrival_offset = " (día siguiente)" if match[9] and match[9] != match[4] else ""
            
            output.append(f'''
            <div class="flight-result">
                <strong>Vuelo {airline_code} {flight_number}</strong><br>
                <strong>Aerolínea:</strong> {airline_name}<br>
                <strong>Fecha:</strong> {departure_date}<br>
                <strong>Horario:</strong> {departure_time} → {arrival_time}{arrival_offset}<br>
                <strong>Ruta:</strong> {origin_name} → {dest_name}
            </div>
            ''')
        
        return '\n'.join(output)
    
    def translate_itinerary(self, itinerary: str, gds_system: str = 'SABRE') -> str:
        """Traduce itinerario según el sistema GDS especificado."""
        if not itinerary.strip():
            return '<div class="error">Por favor, ingrese un itinerario válido.</div>'
        
        try:
            if gds_system.upper() == 'SABRE':
                return self.translate_sabre_itinerary(itinerary)
            elif gds_system.upper() == 'AMADEUS':
                return self.translate_amadeus_itinerary(itinerary)
            elif gds_system.upper() == 'KIU':
                return self.translate_kiu_itinerary(itinerary)
            else:
                return '<div class="error">Sistema GDS no soportado.</div>'
        except Exception as e:
            logger.error(f"Error traduciendo itinerario {gds_system}: {e}")
            return '<div class="error">Error al procesar el itinerario.</div>'

class TicketCalculator:
    """Calculadora de precios de boletos."""
    
    @staticmethod
    def calculate_ticket_price(tarifa: float, fee_consolidador: float, fee_interno: float, porcentaje: float) -> Dict[str, Any]:
        """
        Calcula el precio final del boleto.
        
        Args:
            tarifa: Tarifa base
            fee_consolidador: Fee del consolidador
            fee_interno: Fee interno de la agencia
            porcentaje: Porcentaje de ganancia
        
        Returns:
            Diccionario con el desglose del cálculo
        """
        try:
            suma_base = tarifa + fee_consolidador + fee_interno
            monto_porcentaje = suma_base * (porcentaje / 100)
            precio_final = suma_base + monto_porcentaje
            
            return {
                'tarifa': tarifa,
                'fee_consolidador': fee_consolidador,
                'fee_interno': fee_interno,
                'suma_base': suma_base,
                'porcentaje': porcentaje,
                'monto_porcentaje': monto_porcentaje,
                'precio_final': precio_final,
                'desglose': f"Tarifa: ${tarifa:.2f} + Fee Consolidador: ${fee_consolidador:.2f} + Fee Interno: ${fee_interno:.2f} = ${suma_base:.2f} + {porcentaje}% (${monto_porcentaje:.2f}) = ${precio_final:.2f}"
            }
        except Exception as e:
            logger.error(f"Error calculando precio de boleto: {e}")
            return {'error': str(e)}
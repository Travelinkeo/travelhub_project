# core/amadeus_parser.py

import re
import logging
from typing import Dict, Any, List
from .parsing_utils import _clean_value, _parse_currency_amount

logger = logging.getLogger(__name__)


def parse_amadeus_ticket(plain_text: str) -> Dict[str, Any]:
    """
    Parser específico para boletos de AMADEUS.
    Extrae información de Electronic Ticket Receipt de Amadeus.
    """
    logger.info("--- INICIO DE PARSEO AMADEUS ---")
    
    data = {
        'SOURCE_SYSTEM': 'AMADEUS',
        'pnr': _extract_booking_ref(plain_text),
        'numero_boleto': _extract_ticket_number(plain_text),
        'fecha_emision': _extract_issue_date(plain_text),
        'pasajero': _extract_passenger(plain_text),
        'agencia': _extract_agency(plain_text),
        'vuelos': _extract_flights(plain_text),
        'tarifas': _extract_fares(plain_text),
        'co2_emissions': _extract_co2(plain_text),
    }
    
    logger.info("Datos AMADEUS extraídos correctamente.")
    return data


def _extract_booking_ref(text: str) -> str:
    """Extrae el Booking Reference (PNR)."""
    # El PNR aparece ANTES de "Booking ref:" en línea separada
    match = re.search(r'([A-Z0-9]{6})\s*\n\s*Booking ref:', text, re.MULTILINE)
    if match:
        return match.group(1)
    
    # Fallback: buscar después
    match = re.search(r'Booking ref:\s*\n?\s*([A-Z0-9]{6})', text, re.IGNORECASE)
    if match:
        return match.group(1)
    
    return 'No encontrado'


def _extract_ticket_number(text: str) -> str:
    """Extrae el número de ticket."""
    patterns = [
        r'Ticket:\s*\n?([\d-]+)',
        r'Ticket number\s*:\s*([\d-]+)',
        r'(\d{3}-\d{10})',  # Formato estándar de ticket
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)
    return 'No encontrado'


def _extract_issue_date(text: str) -> str:
    """Extrae la fecha de emisión."""
    match = re.search(r'Issue date:\s*(\d{2}\s+[A-Z]+\s+\d{2,4})', text, re.IGNORECASE)
    if match:
        return match.group(1)
    
    # Formato alternativo al final del documento
    match = re.search(r'Issuing Airline and date\s*:\s*[A-Z\s]+(\d{2}[A-Z]{3}\d{2})', text, re.IGNORECASE)
    return match.group(1) if match else 'No encontrado'


def _extract_passenger(text: str) -> Dict[str, str]:
    """Extrae información del pasajero."""
    passenger = {
        'nombre_completo': 'No encontrado',
        'tipo': 'ADT'  # Default adult
    }
    
    # Buscar nombre del pasajero
    match = re.search(r'Traveler\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\s*(?:\(([A-Z]{3})\))?', text)
    if match:
        passenger['nombre_completo'] = match.group(1)
        if match.group(2):
            passenger['tipo'] = match.group(2)  # CHD, INF, etc.
    
    return passenger


def _extract_agency(text: str) -> Dict[str, str]:
    """Extrae información de la agencia."""
    agency = {
        'nombre': 'No encontrado',
        'direccion': 'No encontrado',
        'telefono': 'No encontrado',
        'iata': 'No encontrado',
        'agente': 'No encontrado'
    }
    
    # Nombre de agencia
    match = re.search(r'Agency\s+([A-Z\s&]+)', text)
    if match:
        agency['nombre'] = match.group(1).strip()
    
    # Dirección
    match = re.search(r'([A-Z0-9\s,.-]+)\s+(?:MIAMI|NEW YORK|CARACAS)', text)
    if match:
        agency['direccion'] = match.group(0).strip()
    
    # Teléfono
    match = re.search(r'Telephone\s+([\d\s-]+)', text)
    if match:
        agency['telefono'] = match.group(1).strip()
    
    # IATA
    match = re.search(r'IATA\s+(\d+)', text)
    if match:
        agency['iata'] = match.group(1)
    
    # Agente
    match = re.search(r'Agent\s+(\d+)', text)
    if match:
        agency['agente'] = match.group(1)
    
    return agency


def _extract_flights(text: str) -> List[Dict[str, Any]]:
    """Extrae información de los vuelos."""
    flights = []
    
    # Buscar todos los números de vuelo (formato: TK0224, AA123, etc)
    flight_numbers = re.findall(r'\b([A-Z]{2})(\d{3,4})\b', text)
    print(f"DEBUG: Vuelos encontrados: {flight_numbers}")
    if not flight_numbers:
        return flights
    
    lines = text.split('\n')
    
    # Procesar cada número de vuelo encontrado
    for airline_code, flight_num in flight_numbers:
        flight_code = f"{airline_code}{flight_num}"
        
        # Buscar el índice donde aparece este vuelo
        flight_idx = -1
        for i, line in enumerate(lines):
            if flight_code in line:
                flight_idx = i
                break
        
        if flight_idx == -1:
            continue
        
        # Extraer contexto (20 líneas antes y después)
        start = max(0, flight_idx - 20)
        end = min(len(lines), flight_idx + 20)
        context = '\n'.join(lines[start:end])
        
        # Buscar ciudades (líneas con solo mayúsculas, excluyendo nombres comunes)
        cities = []
        exclude = ['AIRPORT', 'AIRLINES', 'TURKISH', 'FLOOR', 'IATA', 'BRICKELL', 'TRAVEL', 'MANAGEMENT']
        for i in range(max(0, flight_idx - 15), min(len(lines), flight_idx + 5)):
            city = lines[i].strip()
            if re.match(r'^[A-Z]{3,}(?:\s+[A-Z]+)*$', city) and city not in exclude and len(city) > 2:
                cities.append(city)
                if len(cities) >= 2:
                    break
        
        if len(cities) < 2:
            # Buscar después del vuelo
            for i in range(flight_idx, min(len(lines), flight_idx + 15)):
                city = lines[i].strip()
                if re.match(r'^[A-Z]{3,}(?:\s+[A-Z]+)*$', city) and city not in exclude and len(city) > 2:
                    cities.append(city)
                    if len(cities) >= 2:
                        break
        
        if len(cities) < 2:
            continue
        
        # Extraer fecha y horas
        date_match = re.search(r'(\d{2}[A-Z]{3})\s+(\d{2}:\d{2})', context)
        arrival_match = re.search(r'(\d{2}:\d{2})\s*\n\s*Ok', context)
        
        # Extraer clase
        class_match = re.search(r'^([A-Z])$', context, re.MULTILINE)
        
        # Extraer asiento
        seat_match = re.search(r'^(\d{1,2}[A-Z])$', context, re.MULTILINE)
        
        # Extraer equipaje
        baggage_match = re.search(r'(\d+PC)', context)
        
        if date_match:
            flight = {
                'segmento': len(flights) + 1,
                'origen': cities[0],
                'destino': cities[1] if len(cities) > 1 else 'No encontrado',
                'aerolinea': airline_code,
                'numero_vuelo': flight_code,
                'clase': class_match.group(1) if class_match else 'Y',
                'fecha_salida': date_match.group(1),
                'hora_salida': date_match.group(2),
                'hora_llegada': arrival_match.group(1) if arrival_match else 'No encontrado',
                'estado': 'Ok',
                'asiento': seat_match.group(1) if seat_match else 'No asignado',
                'equipaje': baggage_match.group(1) if baggage_match else '1PC',
                'duracion': 'No encontrado',
                'equipo': 'No encontrado',
                'comida': 'No encontrado'
            }
            flights.append(flight)
    
    return flights


def _old_extract_flights(text: str) -> List[Dict[str, Any]]:
    """Método antiguo - mantener por referencia."""
    flights = []
    lines = text.split('\n')
    
    i = 0
    while i < len(lines):
        line = lines[i]
        if re.match(r'(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)', line):
            # Extraer bloque de vuelo (siguiente 30 líneas)
            flight_block = '\n'.join(lines[i:min(i+30, len(lines))])
            
            # Buscar ciudades (origen y destino)
            cities = []
            for j in range(i+1, min(i+10, len(lines))):
                if re.match(r'^[A-Z]{3,}(?:\s+[A-Z]+)*$', lines[j].strip()):
                    cities.append(lines[j].strip())
                if len(cities) >= 2:
                    break
            
            # Extraer número de vuelo
            flight_num_match = re.search(r'\b([A-Z]{2})(\d{3,4})\b', flight_block)
            
            # Extraer clase (letra sola en una línea)
            class_match = re.search(r'^([A-Z])$', flight_block, re.MULTILINE)
            
            # Extraer fecha y horas
            date_match = re.search(r'(\d{2}[A-Z]{3})\s+(\d{2}:\d{2})', flight_block)
            arrival_match = re.search(r'(\d{2}:\d{2})\s*\n\s*Ok', flight_block)
            
            # Extraer asiento (número+letra en línea sola)
            seat_match = re.search(r'^(\d{1,2}[A-Z])$', flight_block, re.MULTILINE)
            
            # Extraer equipaje
            baggage_match = re.search(r'(\d+PC)', flight_block)
            
            # Extraer duración
            duration_match = re.search(r'(\d{2}:\d{2})\s*\(Non Stop\)', flight_block)
            
            # Extraer equipo
            equipment_match = re.search(r'Equipment\s*\n\s*([\w\s-]+?)\n', flight_block)
            
            if flight_num_match and date_match and len(cities) >= 2:
                flight = {
                    'segmento': len(flights) + 1,
                    'origen': cities[0],
                    'destino': cities[1],
                    'aerolinea': flight_num_match.group(1),
                    'numero_vuelo': f"{flight_num_match.group(1)}{flight_num_match.group(2)}",
                    'clase': class_match.group(1) if class_match else 'No encontrado',
                    'fecha_salida': date_match.group(1),
                    'hora_salida': date_match.group(2),
                    'hora_llegada': arrival_match.group(1) if arrival_match else 'No encontrado',
                    'estado': 'Ok',
                    'asiento': seat_match.group(1) if seat_match else 'No encontrado',
                    'equipaje': baggage_match.group(1) if baggage_match else 'No encontrado',
                    'duracion': duration_match.group(1) if duration_match else 'No encontrado',
                    'equipo': equipment_match.group(1).strip() if equipment_match else 'No encontrado',
                    'comida': 'No encontrado'
                }
                
                flights.append(flight)
            
            i += 30
        else:
            i += 1
    
    return flights


def _extract_flight_details(text: str, flight_number: str) -> Dict[str, str]:
    """Extrae detalles adicionales de un vuelo específico."""
    details = {
        'equipaje': 'No encontrado',
        'asiento': 'No encontrado',
        'duracion': 'No encontrado',
        'equipo': 'No encontrado',
        'comida': 'No encontrado'
    }
    
    # Buscar la sección del vuelo
    pattern = rf'{flight_number}.*?(?=(?:[A-Z]{{2}}\d{{3,4}}|Receipt|$))'
    match = re.search(pattern, text, re.DOTALL)
    
    if match:
        section = match.group(0)
        
        # Equipaje
        baggage_match = re.search(r'(\d+PC)', section)
        if baggage_match:
            details['equipaje'] = baggage_match.group(1)
        
        # Asiento
        seat_match = re.search(r'(\d{1,2}[A-Z])', section)
        if seat_match:
            details['asiento'] = seat_match.group(1)
        
        # Duración
        duration_match = re.search(r'(\d{2}:\d{2})\s*\(Non Stop\)', section)
        if duration_match:
            details['duracion'] = duration_match.group(1)
        
        # Equipo
        equipment_match = re.search(r'Equipment\s+([\w\s-]+)', section)
        if equipment_match:
            details['equipo'] = equipment_match.group(1).strip()
        
        # Comida
        meal_match = re.search(r'Flight Meal\s+(\w+)', section)
        if meal_match:
            details['comida'] = meal_match.group(1)
    
    return details


def _extract_fares(text: str) -> Dict[str, Any]:
    """Extrae información de tarifas y pagos."""
    fares = {
        'forma_pago': 'No encontrado',
        'tarifa_base': 'No encontrado',
        'impuestos': [],
        'cargos_aerolinea': 'No encontrado',
        'total': 'No encontrado',
        'restricciones': 'No encontrado'
    }
    
    # Forma de pago
    match = re.search(r'Form of payment\s*:\s*([A-Z]+)', text)
    if match:
        fares['forma_pago'] = match.group(1)
    
    # Tarifa base
    match = re.search(r'Air Fare\s*:\s*([A-Z]{3}\s*[\d,.]+)', text)
    if match:
        fares['tarifa_base'] = match.group(1)
    
    # Impuestos (múltiples líneas)
    tax_pattern = r'([A-Z]{3}\s*[\d,.]+)([A-Z]{2})'
    tax_matches = re.finditer(tax_pattern, text)
    for match in tax_matches:
        fares['impuestos'].append({
            'monto': match.group(1).strip(),
            'codigo': match.group(2)
        })
    
    # Cargos de aerolínea
    match = re.search(r'Airline Surcharges\s*:\s*([A-Z]{3}\s*[\d,.]+[A-Z]{2})', text)
    if match:
        fares['cargos_aerolinea'] = match.group(1)
    
    # Total
    match = re.search(r'Total Amount\s*:\s*([A-Z]{3}\s*[\d,.]+)', text)
    if match:
        fares['total'] = match.group(1)
    
    # Restricciones
    match = re.search(r'Restriction\(s\)/Endorsements\s*:\s*([A-Z0-9/\s]+)', text)
    if match:
        fares['restricciones'] = match.group(1).strip()
    
    return fares


def _extract_co2(text: str) -> str:
    """Extrae información de emisiones de CO2."""
    match = re.search(r'CO2 EMISSIONS IS\s*([\d,.]+)\s*KG/PERSON', text, re.IGNORECASE)
    return match.group(1) if match else 'No encontrado'

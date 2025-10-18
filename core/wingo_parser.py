"""
Parser para boletos de WINGO (Reservas Web)
"""
import re


def parse_wingo_ticket(text):
    """
    Parsea un boleto de WINGO y retorna un diccionario normalizado.
    """
    from datetime import datetime
    
    data = {
        'SOURCE_SYSTEM': 'WINGO',
        'pnr': None,
        'fecha_creacion': datetime.now().strftime('%d/%m/%Y'),
        'pasajero': {},
        'numero_boleto': None,
        'vuelos': [],
        'equipaje': {}
    }
    
    # PNR
    pnr_match = re.search(r'(?:C[óo]digo de reserva|reserva)\s+([A-Z0-9]{6})', text, re.IGNORECASE | re.DOTALL)
    if pnr_match:
        data['pnr'] = pnr_match.group(1)
    
    # Pasajero
    pasajero_match = re.search(r'Contacto\s+([A-Z\s]+)\s+Documento', text, re.IGNORECASE)
    if pasajero_match:
        data['pasajero'] = {
            'nombre_completo': pasajero_match.group(1).strip(),
            'tipo': 'ADT'
        }
    
    # WINGO no genera número de boleto (low-cost)
    
    # Vuelo de ida
    ida_match = re.search(
        r'Vuelo de ida.*?([A-Za-z]{3}, \d{1,2} [A-Za-z]{3})\s+(\d{2}:\d{2} [AP]M).*?Directo\s+(\d+h \d+min)\s+(\d{2}:\d{2} [AP]M)\s+([A-Za-z]+)\s+\(([A-Z]{3})\)\s+([A-Za-z]+)\s+\(([A-Z]{3})\)',
        text, re.DOTALL
    )
    if ida_match:
        vuelo_ida = {
            'numero_vuelo': 'WINGO',
            'origen': ida_match.group(5),
            'codigo_origen': ida_match.group(6),
            'fecha_salida': ida_match.group(1),
            'hora_salida': ida_match.group(2),
            'destino': ida_match.group(7),
            'codigo_destino': ida_match.group(8),
            'hora_llegada': ida_match.group(4),
            'duracion': ida_match.group(3),
            'aerolinea': 'Wingo',
            'cabina': 'GO BASIC'
        }
        data['vuelos'].append(vuelo_ida)
    
    # Vuelo de vuelta
    vuelta_match = re.search(
        r'Vuelo de vuelta.*?([A-Za-z]{3}, \d{1,2} [A-Za-z]{3})\s+(\d{2}:\d{2} [AP]M).*?Directo\s+(\d+h \d+min)\s+(\d{2}:\d{2} [AP]M)\s+([A-Za-z]+)\s+\(([A-Z]{3})\)\s+([A-Za-z]+)\s+\(([A-Z]{3})\)',
        text, re.DOTALL
    )
    if vuelta_match:
        vuelo_vuelta = {
            'numero_vuelo': 'WINGO',
            'origen': vuelta_match.group(5),
            'codigo_origen': vuelta_match.group(6),
            'fecha_salida': vuelta_match.group(1),
            'hora_salida': vuelta_match.group(2),
            'destino': vuelta_match.group(7),
            'codigo_destino': vuelta_match.group(8),
            'hora_llegada': vuelta_match.group(4),
            'duracion': vuelta_match.group(3),
            'aerolinea': 'Wingo',
            'cabina': 'GO BASIC'
        }
        data['vuelos'].append(vuelo_vuelta)
    
    return data

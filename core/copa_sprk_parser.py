"""
Parser para boletos de COPA SPRK (Copa Airlines)
"""
import re


def parse_copa_sprk_ticket(text):
    """
    Parsea un boleto de COPA SPRK y retorna un diccionario normalizado.
    """
    data = {
        'SOURCE_SYSTEM': 'COPA_SPRK',
        'pnr': None,
        'fecha_creacion': None,
        'pasajero': {},
        'numero_boleto': None,
        'vuelos': [],
        'equipaje': {}
    }
    
    # PNR
    pnr_match = re.search(r'Localizador de reserva\s+([A-Z0-9]{6})', text)
    if pnr_match:
        data['pnr'] = pnr_match.group(1)
    
    # Número de boleto
    boleto_match = re.search(r'Billete electr[óo]nico\s+(\d+)', text)
    if boleto_match:
        data['numero_boleto'] = boleto_match.group(1)
    
    # Fecha de emisión
    fecha_match = re.search(r'Fecha de emisi[óo]n\s+(\d{2}[A-Z]{3}\.\d{2})', text)
    if fecha_match:
        data['fecha_creacion'] = fecha_match.group(1)
    
    # Pasajero
    pasajero_match = re.search(r'(MR|MRS|MS)\s+([A-Z\s]+)\s+\(ADT\)', text)
    if pasajero_match:
        data['pasajero'] = {
            'nombre_completo': f"{pasajero_match.group(1)} {pasajero_match.group(2).strip()}",
            'tipo': 'ADT'
        }
    
    # Vuelos
    vuelo_pattern = r'Copa Airlines\s+(\d+)\s+([^,]+),\s+([A-Z]{2})\s+([A-Z]{2}\. \d{2}[A-Z]{3}\.)\s+(\d{2}:\d{2})\s+([^,]+),\s+([A-Z]{2})\s+([A-Z]{2}\. \d{2}[A-Z]{3}\.)\s+(\d{2}:\d{2})\s+([A-Z])\s+([A-Z])'
    
    for match in re.finditer(vuelo_pattern, text):
        vuelo = {
            'numero_vuelo': f"CM{match.group(1)}",
            'origen': match.group(2).strip(),
            'codigo_origen': match.group(3),
            'fecha_salida': match.group(4),
            'hora_salida': match.group(5),
            'destino': match.group(6).strip(),
            'codigo_destino': match.group(7),
            'fecha_llegada': match.group(8),
            'hora_llegada': match.group(9),
            'clase': match.group(10),
            'cabina': match.group(11),
            'aerolinea': 'Copa Airlines'
        }
        data['vuelos'].append(vuelo)
    
    return data

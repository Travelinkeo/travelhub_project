"""
Parser para boletos de TK Connect (Turkish Airlines)
"""
import re
from datetime import datetime


def parse_tk_connect_ticket(text):
    """
    Parsea un boleto de TK Connect y retorna un diccionario normalizado.
    """
    data = {
        'SOURCE_SYSTEM': 'TK_CONNECT',
        'pnr': None,
        'fecha_creacion': None,
        'estado': None,
        'oficina_emision': None,
        'pasajero': {},
        'numero_boleto': None,
        'vuelos': [],
        'equipaje': {}
    }
    
    # PNR
    pnr_match = re.search(r'Identificación del pedido\s+([A-Z0-9]{6})', text)
    if pnr_match:
        data['pnr'] = pnr_match.group(1)
    
    # Fecha de creación
    fecha_match = re.search(r'Fecha de creación\s+(\d{1,2}\s+\w+,\s+\d{4})', text)
    if fecha_match:
        data['fecha_creacion'] = fecha_match.group(1)
    
    # Estado
    estado_match = re.search(r'Estado\s+([A-Z]+)', text)
    if estado_match:
        data['estado'] = estado_match.group(1)
    
    # Oficina de emisión
    oficina_match = re.search(r'Oficina de emisión\s+(.+)', text)
    if oficina_match:
        data['oficina_emision'] = oficina_match.group(1).strip()
    
    # Pasajero
    pasajero_match = re.search(r'(Ms\.|Mr\.|Mrs\.)\s+([A-Za-z]+)\s+([A-Z\-]+)', text)
    if pasajero_match:
        data['pasajero']['titulo'] = pasajero_match.group(1)
        data['pasajero']['nombre'] = pasajero_match.group(2)
        data['pasajero']['apellido'] = pasajero_match.group(3)
        data['pasajero']['nombre_completo'] = f"{pasajero_match.group(3)}/{pasajero_match.group(2)}"
    
    # Fecha de nacimiento
    dob_match = re.search(r'Date of Birth\s+(\d{1,2}\s+\w+,\s+\d{4})', text)
    if dob_match:
        data['pasajero']['fecha_nacimiento'] = dob_match.group(1)
    
    # Contacto
    phone_match = re.search(r'\+(\d+)', text)
    if phone_match:
        data['pasajero']['telefono'] = f"+{phone_match.group(1)}"
    
    email_match = re.search(r'([A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,})', text, re.IGNORECASE)
    if email_match:
        data['pasajero']['email'] = email_match.group(1)
    
    # Número de boleto
    ticket_match = re.search(r'Ticket Number\s+(\d+)', text, re.IGNORECASE)
    if ticket_match:
        data['numero_boleto'] = ticket_match.group(1)
    else:
        # Buscar patrón alternativo
        ticket_match2 = re.search(r'(\d{13})', text)
        if ticket_match2:
            data['numero_boleto'] = ticket_match2.group(1)
    
    # Vuelos
    vuelos_pattern = r'(TK\d+)\s+.*?\n([A-Za-z\s\(\)]+)\s+•\s+(\d{2}:\d{2})\s+(\d{1,2}\s+\w+,\s+\w+\.)\s+([A-Za-z\s\(\)]+)\s+•\s+(\d{2}:\d{2})\s+(\d{1,2}\s+\w+,\s+\w+\.)\s+Turkish Airlines\s+([A-Z,\s]+)\s+\|\s+([A-Z]+)'
    
    for match in re.finditer(vuelos_pattern, text):
        vuelo = {
            'numero_vuelo': match.group(1),
            'origen': match.group(2).strip(),
            'hora_salida': match.group(3),
            'fecha_salida': match.group(4),
            'destino': match.group(5).strip(),
            'hora_llegada': match.group(6),
            'fecha_llegada': match.group(7),
            'clase_reserva': match.group(8).strip(),
            'cabina': match.group(9).strip()
        }
        data['vuelos'].append(vuelo)
    
    # Equipaje
    equipaje_match = re.search(r'Checked Baggage\s+(\d+)\s+piezas', text)
    if equipaje_match:
        data['equipaje']['facturado'] = f"{equipaje_match.group(1)} piezas"
    
    cabina_match = re.search(r'Cabin Baggage\s+(\d+)\s+pieza\s+x\s+(\d+)\s+kilogramos', text)
    if cabina_match:
        data['equipaje']['cabina'] = f"{cabina_match.group(1)} pieza x {cabina_match.group(2)} kg"
    
    return data

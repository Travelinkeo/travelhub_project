"""
Parser para boletos de COPA SPRK (Copa Airlines)
"""
import re


def parse_copa_sprk_ticket(text):
    """
    Parsea un boleto de COPA SPRK y retorna un diccionario normalizado.
    TODO: Implementar cuando se tenga un boleto de ejemplo.
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
    
    # TODO: Implementar extracción de datos cuando se tenga formato real
    # Ejemplo de estructura esperada:
    # - PNR
    # - Nombre pasajero
    # - Número de boleto
    # - Vuelos (origen, destino, fechas, horas)
    # - Equipaje
    
    return data

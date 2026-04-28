#!/usr/bin/env python
"""
Demostración de la normalización de aerolíneas en TravelHub.
"""

import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from core.airline_utils import normalize_airline_name

def demo_airline_normalization():
    """Demuestra cómo se normalizan los nombres de aerolíneas."""
    print("=== DEMO: NORMALIZACION DE AEROLINEAS ===\n")
    
    # Casos de prueba reales que podrían venir de boletos
    test_cases = [
        # (nombre_crudo_del_boleto, numero_vuelo, descripcion)
        ("AMERICAN AIRLINES", "AA1234", "Nombre completo en boleto"),
        ("AVIANCA", "AV567", "Nombre corto en boleto"),
        ("LATAM AIRLINES", "LA890", "Variación del nombre"),
        ("COPA", "CM123", "Nombre abreviado"),
        ("CONVIASA VENEZUELA", "V0456", "Con país en el nombre"),
        ("AVIOR AIRLINES C.A.", "9V789", "Con sufijo corporativo"),
        ("UNKNOWN AIRLINE XYZ", "XX999", "Aerolínea no en catálogo"),
        ("", "AV123", "Nombre vacío, solo número de vuelo"),
        ("SOME AIRLINE", "", "Solo nombre, sin vuelo"),
    ]
    
    print("Formato: [Nombre Original] -> [Nombre Normalizado] (Vuelo: [Número])\n")
    
    for raw_name, flight_number, description in test_cases:
        normalized = normalize_airline_name(raw_name, flight_number)
        
        print(f"Caso: {description}")
        print(f"  Original: '{raw_name}'")
        print(f"  Vuelo: {flight_number}")
        print(f"  Normalizado: '{normalized}'")
        print()

def demo_parser_integration():
    """Demuestra cómo se integra con los parsers de boletos."""
    print("=== DEMO: INTEGRACION CON PARSERS ===\n")
    
    # Simular datos que vendrían de un parser de boleto
    mock_ticket_data = {
        "raw_airline_name": "AVIANCA COLOMBIA",
        "flight_number": "AV123",
        "passenger_name": "PEREZ/JUAN",
        "pnr": "ABC123"
    }
    
    print("Datos originales del boleto:")
    for key, value in mock_ticket_data.items():
        print(f"  {key}: {value}")
    
    # Normalizar el nombre de la aerolínea
    normalized_airline = normalize_airline_name(
        mock_ticket_data["raw_airline_name"], 
        mock_ticket_data["flight_number"]
    )
    
    print(f"\nDespués de la normalización:")
    print(f"  Aerolínea normalizada: {normalized_airline}")
    
    print(f"\nBeneficios:")
    print(f"  - Consistencia en la base de datos")
    print(f"  - Mejor experiencia de usuario")
    print(f"  - Facilita reportes y análisis")
    print(f"  - Reduce duplicados por variaciones de nombre")

if __name__ == '__main__':
    demo_airline_normalization()
    demo_parser_integration()
    print("=== DEMO COMPLETADA ===")
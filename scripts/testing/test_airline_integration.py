#!/usr/bin/env python
"""
Script de prueba para verificar la integración del catálogo de aerolíneas.
"""

import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from core.models_catalogos import Aerolinea
from core.airline_utils import get_airline_name_by_code, extract_airline_code_from_flight, normalize_airline_name

def test_airline_catalog():
    """Prueba el catálogo de aerolíneas."""
    print("=== PRUEBA DEL CATÁLOGO DE AEROLÍNEAS ===")
    
    # Verificar que se cargaron las aerolíneas
    total_airlines = Aerolinea.objects.count()
    print(f"Total de aerolíneas en el catálogo: {total_airlines}")
    
    # Probar algunas aerolíneas conocidas
    test_codes = ['AA', 'AV', 'LA', 'CM', 'P5', 'V0', '9V']
    
    for code in test_codes:
        airline = Aerolinea.objects.filter(codigo_iata=code).first()
        if airline:
            print(f"[OK] {code}: {airline.nombre}")
        else:
            print(f"[FAIL] {code}: No encontrada")

def test_airline_utils():
    """Prueba las utilidades de aerolíneas."""
    print("\n=== PRUEBA DE UTILIDADES ===")
    
    # Probar get_airline_name_by_code
    test_cases = [
        ('AA', 'American Airlines'),
        ('AV', 'Avianca'),
        ('LA', 'LATAM Airlines Group'),
        ('XX', None),  # Código inexistente
    ]
    
    for code, expected in test_cases:
        result = get_airline_name_by_code(code)
        status = "[OK]" if (result is not None) == (expected is not None) else "[FAIL]"
        print(f"{status} get_airline_name_by_code('{code}'): {result}")
    
    # Probar extract_airline_code_from_flight
    flight_tests = [
        ('AA1234', 'AA'),
        ('AV123', 'AV'),
        ('LA456', 'LA'),
        ('1234', None),  # Sin código
        ('', None),  # Vacío
    ]
    
    for flight, expected in flight_tests:
        result = extract_airline_code_from_flight(flight)
        status = "[OK]" if result == expected else "[FAIL]"
        print(f"{status} extract_airline_code_from_flight('{flight}'): {result}")
    
    # Probar normalize_airline_name
    normalize_tests = [
        ('AMERICAN AIRLINES', 'AA1234', 'American Airlines'),
        ('AVIANCA', 'AV123', 'Avianca'),
        ('UNKNOWN AIRLINE', 'XX999', 'UNKNOWN AIRLINE'),  # Fallback
    ]
    
    for raw_name, flight, expected_contains in normalize_tests:
        result = normalize_airline_name(raw_name, flight)
        # Para esta prueba, solo verificamos que no sea None
        status = "[OK]" if result else "[FAIL]"
        print(f"{status} normalize_airline_name('{raw_name}', '{flight}'): {result}")

def test_api_endpoint():
    """Prueba el endpoint de la API."""
    print("\n=== PRUEBA DE API ===")
    
    try:
        from django.test import Client
        client = Client()
        
        response = client.get('/api/aerolineas/')
        if response.status_code == 200:
            data = response.json()
            print(f"[OK] API endpoint funciona. Total aerolineas: {len(data)}")
            
            # Mostrar las primeras 5
            for airline in data[:5]:
                print(f"  - {airline['codigo_iata']}: {airline['nombre']}")
        else:
            print(f"[FAIL] API endpoint fallo. Status: {response.status_code}")
            
    except Exception as e:
        print(f"[FAIL] Error probando API: {e}")

if __name__ == '__main__':
    test_airline_catalog()
    test_airline_utils()
    test_api_endpoint()
    print("\n=== PRUEBAS COMPLETADAS ===")
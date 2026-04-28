#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Script para probar parser SABRE con múltiples ejemplos con precio"""
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')

import django
django.setup()

from core.parsers.sabre_parser import SabreParser
import pdfplumber

# Lista de PDFs con precio
test_files = [
    r"C:\Users\ARMANDO\Downloads\Boletos\WINGO\Recibo de pasaje electrónico, 13 marzo para OSCAR DUQUE.pdf",
    r"C:\Users\ARMANDO\Downloads\Recibo de pasaje electrónico, 19 noviembre para ALIKY DE SOUSA.pdf",
    r"C:\Users\ARMANDO\Downloads\Recibo de pasaje electrónico, 21 diciembre para LAURA CRISTINA ARROYAVE.pdf",
    r"C:\Users\ARMANDO\Downloads\Recibo de pasaje electrónico, 26 diciembre para BRIGIDA DEL CARMEN ABREO DURAN.pdf",
    r"C:\Users\ARMANDO\Downloads\Recibo de pasaje electrónico, 13 febrero para OSCAR DUQUE.pdf",
]

parser = SabreParser()

print("="*80)
print("PRUEBA DE PARSER SABRE CON BOLETOS CON PRECIO")
print("="*80)

for file_path in test_files:
    if not Path(file_path).exists():
        print(f"\nNo encontrado: {Path(file_path).name}")
        continue
    
    print(f"\n{'='*80}")
    print(f"Archivo: {Path(file_path).name}")
    print(f"{'='*80}")
    
    # Extraer texto
    with pdfplumber.open(file_path) as pdf:
        text = ""
        for page in pdf.pages:
            text += (page.extract_text() or "") + "\n"
    
    # Verificar detección
    can_parse = parser.can_parse(text)
    print(f"Deteccion SABRE: {'SI' if can_parse else 'NO'}")
    
    if not can_parse:
        continue
    
    # Parsear
    try:
        result = parser.parse(text, "")
        result_dict = result.to_dict()
        
        print(f"\nDATOS EXTRAIDOS:")
        print(f"  PNR: {result_dict.get('pnr')}")
        print(f"  Ticket #: {result_dict.get('ticket_number')}")
        print(f"  Passenger: {result_dict.get('passenger_name')}")
        print(f"  Airline: {result_dict.get('airline_name')}")
        print(f"  Total: {result_dict.get('total')}")
        print(f"  Flights: {len(result_dict.get('flights', []))}")
        
        # Mostrar tarifas detalladas
        fares = result_dict.get('tarifas', {})
        if fares:
            print(f"\nTARIFAS:")
            print(f"  Base Fare: {fares.get('fare_currency')} {fares.get('fare_amount')}")
            print(f"  Total: {fares.get('total_currency')} {fares.get('total_amount')}")
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

print(f"\n{'='*80}")
print("PRUEBA COMPLETADA")
print(f"{'='*80}")

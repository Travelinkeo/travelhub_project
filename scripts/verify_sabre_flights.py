#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')

import django
django.setup()

from core.parsers.sabre_parser import SabreParser
import pdfplumber

pdf_path = r"C:\Users\ARMANDO\Downloads\Recibo de pasaje electrónico, 19 noviembre para ALIKY DE SOUSA.pdf"

print("="*80)
print("VERIFICACIÓN DE EXTRACCIÓN DE VUELOS - SABRE PARSER")
print("="*80)

# Extraer texto
with pdfplumber.open(pdf_path) as pdf:
    text = '\n'.join([p.extract_text() or '' for p in pdf.pages])

print(f"\n1. Texto extraído: {len(text)} caracteres")

# Parsear
parser = SabreParser()
print(f"\n2. ¿Puede parsear? {parser.can_parse(text)}")

if parser.can_parse(text):
    result = parser.parse(text, "")
    
    print(f"\n3. Resultado del parseo:")
    print(f"   - PNR: {result.pnr}")
    print(f"   - Ticket: {result.ticket_number}")
    print(f"   - Passenger: {result.passenger_name}")
    print(f"   - Vuelos en result.flights: {len(result.flights)}")
    
    if result.flights:
        print(f"\n4. Detalles de vuelos:")
        for i, flight in enumerate(result.flights, 1):
            print(f"\n   Vuelo {i}:")
            print(f"     - Aerolínea: {flight.get('aerolinea')}")
            print(f"     - Número: {flight.get('numero_vuelo')}")
            print(f"     - Origen: {flight.get('origen')}")
            print(f"     - Destino: {flight.get('destino')}")
            print(f"     - Fecha: {flight.get('fecha_salida')}")
    else:
        print("\n   ❌ NO SE EXTRAJERON VUELOS")
    
    # Verificar to_dict()
    dict_result = result.to_dict()
    print(f"\n5. Vuelos en to_dict()['vuelos']: {len(dict_result.get('vuelos', []))}")
    print(f"   Vuelos en to_dict()['flights']: {len(dict_result.get('flights', []))}")
    
    if dict_result.get('vuelos'):
        print(f"\n6. Primer vuelo en dict:")
        print(f"   {dict_result['vuelos'][0]}")

print("\n" + "="*80)

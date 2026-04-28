#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script para probar el nuevo flujo de parseo integrado
"""
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')

import django
django.setup()

from django.core.files.uploadedfile import SimpleUploadedFile

# Ruta del boleto SABRE
test_file = r"C:\Users\ARMANDO\Downloads\Recibo de pasaje electrónico, 19 noviembre para ALIKY DE SOUSA.pdf"

print("="*80)
print("PRUEBA DE PARSEO INTEGRADO CON NUEVOS PARSERS")
print("="*80)
print(f"\nArchivo: {Path(test_file).name}")

# Leer archivo
with open(test_file, 'rb') as f:
    file_content = f.read()

# Crear uploaded file simulado
uploaded_file = SimpleUploadedFile(
    name=Path(test_file).name,
    content=file_content,
    content_type='application/pdf'
)

# Probar parseo
from core.services.ticket_parser_service import orquestar_parseo_de_boleto

print("\n1. Ejecutando orquestar_parseo_de_boleto...")
datos, mensaje = orquestar_parseo_de_boleto(uploaded_file)

print(f"\n2. Resultado del parseo:")
print(f"   Mensaje: {mensaje}")

if datos:
    print(f"\n3. Datos extraídos:")
    print(f"   SOURCE_SYSTEM: {datos.get('SOURCE_SYSTEM')}")
    print(f"   PNR: {datos.get('pnr')}")
    print(f"   Ticket: {datos.get('ticket_number') or datos.get('numero_boleto')}")
    print(f"   Passenger: {datos.get('passenger_name') or datos.get('pasajero', {}).get('nombre_completo')}")
    print(f"   Airline: {datos.get('airline_name')}")
    print(f"   Total: {datos.get('total')}")
    print(f"   Flights: {len(datos.get('flights', datos.get('vuelos', [])))}")
    
    # Probar generación de PDF
    print(f"\n4. Probando generación de PDF...")
    from core.services.ticket_parser_service import generar_pdf_en_memoria
    
    try:
        pdf_bytes = generar_pdf_en_memoria(datos)
        if pdf_bytes:
            output_path = r"c:\Users\ARMANDO\travelhub_project\test_integrated_sabre.pdf"
            with open(output_path, 'wb') as f:
                f.write(pdf_bytes)
            print(f"   ✅ PDF generado: {output_path}")
            print(f"   Tamaño: {len(pdf_bytes)} bytes")
        else:
            print("   ❌ PDF generation returned None")
    except Exception as e:
        print(f"   ❌ Error generando PDF: {e}")
        import traceback
        traceback.print_exc()
else:
    print(f"\n❌ No se pudieron extraer datos")

print("\n" + "="*80)
print("PRUEBA COMPLETADA")
print("="*80)

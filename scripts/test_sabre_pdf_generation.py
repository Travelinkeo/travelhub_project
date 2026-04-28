#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script para probar generación de PDF con boleto SABRE
"""
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')

import django
django.setup()

from core.parsers.sabre_parser import SabreParser
from core.services.ticket_parser_service import generar_pdf_en_memoria
import pdfplumber

# Boleto SABRE con precio (del análisis anterior)
test_file = r"C:\Users\ARMANDO\Downloads\Recibo de pasaje electrónico, 19 noviembre para ALIKY DE SOUSA.pdf"
output_pdf = r"c:\Users\ARMANDO\travelhub_project\test_sabre_output.pdf"

print("="*80)
print("PRUEBA DE GENERACION DE PDF CON SABRE")
print("="*80)
print(f"\nArchivo de entrada: {Path(test_file).name}")

# Extraer texto del PDF
print("\n1. Extrayendo texto del PDF...")
with pdfplumber.open(test_file) as pdf:
    text = ""
    for page in pdf.pages:
        text += (page.extract_text() or "") + "\n"

print(f"   Texto extraido: {len(text)} caracteres")

# Parsear con SABRE parser
print("\n2. Parseando con SABRE parser...")
parser = SabreParser()

if not parser.can_parse(text):
    print("   ERROR: El parser SABRE no detecta este boleto")
    sys.exit(1)

print("   Deteccion: OK")

try:
    result = parser.parse(text, "")
    result_dict = result.to_dict()
    
    print("\n3. Datos extraidos:")
    print(f"   PNR: {result_dict.get('pnr')}")
    print(f"   Ticket: {result_dict.get('ticket_number')}")
    print(f"   Passenger: {result_dict.get('passenger_name')}")
    print(f"   Airline: {result_dict.get('airline_name')}")
    print(f"   Total: {result_dict.get('total')}")
    print(f"   Flights: {len(result_dict.get('flights', []))}")
    
    # Generar PDF
    print("\n4. Generando PDF...")
    
    # Buscar plantilla de boleto
    from django.conf import settings
    template_path = Path(settings.BASE_DIR) / "core" / "templates" / "boletos"
    
    print(f"   Buscando plantillas en: {template_path}")
    
    if template_path.exists():
        templates = list(template_path.glob("*.html"))
        print(f"   Plantillas encontradas: {len(templates)}")
        for t in templates:
            print(f"     - {t.name}")
    
    # Intentar generar PDF
    try:
        pdf_bytes = generar_pdf_en_memoria(result_dict)
        
        # Guardar PDF
        with open(output_pdf, 'wb') as f:
            f.write(pdf_bytes)
        
        print(f"\n   PDF generado exitosamente!")
        print(f"   Ubicacion: {output_pdf}")
        print(f"   Tamano: {len(pdf_bytes)} bytes")
        
    except Exception as e:
        print(f"\n   ERROR al generar PDF: {e}")
        import traceback
        traceback.print_exc()
        
        # Intentar método alternativo si existe
        print("\n   Intentando metodo alternativo...")
        from django.template.loader import render_to_string
        from weasyprint import HTML
        
        # Buscar plantilla SABRE
        template_name = "core/tickets/ticket_template_sabre.html"
        try:
            html_content = render_to_string(template_name, {'boleto': result_dict})
            pdf_bytes = HTML(string=html_content).write_pdf()
            
            with open(output_pdf, 'wb') as f:
                f.write(pdf_bytes)
            
            print(f"   PDF generado con metodo alternativo!")
            print(f"   Ubicacion: {output_pdf}")
            print(f"   Tamano: {len(pdf_bytes)} bytes")
            
        except Exception as e2:
            print(f"   ERROR en metodo alternativo: {e2}")
            import traceback
            traceback.print_exc()
    
except Exception as e:
    print(f"\nERROR durante el parseo: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*80)
print("PRUEBA COMPLETADA")
print("="*80)

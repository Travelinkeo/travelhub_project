#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script para probar los parsers actuales con los boletos de muestra.
Genera un reporte JSON comparando la salida de cada parser.
"""

import os
import sys
import json
from pathlib import Path

# Setup Django
sys.path.insert(0, str(Path(__file__).parent.parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')

import django
django.setup()

from core.ticket_parser import extract_data_from_text
import pdfplumber
from email import policy
from email.parser import BytesParser

DATASET_PATH = r"C:\Users\ARMANDO\Downloads\Boletos"
OUTPUT_PATH = Path(__file__).parent.parent / "parser_test_results.json"

def extract_text_from_file(file_path):
    """Extrae texto de PDF o EML"""
    if file_path.endswith('.pdf'):
        text = ""
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text += (page.extract_text() or "") + "\n"
        return text, ""
    
    elif file_path.endswith('.eml'):
        with open(file_path, 'rb') as f:
            msg = BytesParser(policy=policy.default).parse(f)
            
            plain_text = ""
            html_text = ""
            
            if msg.is_multipart():
                for part in msg.walk():
                    ctype = part.get_content_type()
                    try:
                        if ctype == 'text/html':
                            html_text = part.get_content()
                        elif ctype == 'text/plain':
                            plain_text = part.get_content()
                    except:
                        pass
            else:
                content = msg.get_content()
                if msg.get_content_type() == 'text/html':
                    html_text = content
                else:
                    plain_text = content
                    
            return plain_text or html_text, html_text
    
    return None, None

def test_parser_on_samples(gds_folder, max_samples=3):
    """Prueba el parser en las primeras N muestras de una carpeta GDS"""
    folder_path = Path(DATASET_PATH) / gds_folder
    results = []
    
    files = list(folder_path.glob("*.*"))[:max_samples]
    
    for file_path in files:
        print(f"  Procesando: {file_path.name}")
        
        plain_text, html_text = extract_text_from_file(str(file_path))
        
        if not plain_text:
            print(f"    ⚠️ No se pudo extraer texto")
            continue
            
        try:
            parsed_data = extract_data_from_text(plain_text, html_text, str(file_path))
            
            result = {
                "file": file_path.name,
                "gds_folder": gds_folder,
                "detected_system": parsed_data.get('SOURCE_SYSTEM', 'UNKNOWN'),
                "extracted_fields": {
                    "ticket_number": parsed_data.get('ticket_number') or parsed_data.get('NUMERO_DE_BOLETO') or parsed_data.get('numero_boleto'),
                    "pnr": parsed_data.get('pnr') or parsed_data.get('CODIGO_RESERVA') or parsed_data.get('SOLO_CODIGO_RESERVA'),
                    "passenger": parsed_data.get('passenger_name') or parsed_data.get('NOMBRE_DEL_PASAJERO'),
                    "airline": parsed_data.get('airline_name') or parsed_data.get('NOMBRE_AEROLINEA'),
                    "total": parsed_data.get('total') or parsed_data.get('TOTAL'),
                    "flights_count": len(parsed_data.get('vuelos', parsed_data.get('flights', [])))
                },
                "all_keys": list(parsed_data.keys())
            }
            
            results.append(result)
            print(f"    ✅ Sistema detectado: {result['detected_system']}")
            
        except Exception as e:
            print(f"    ❌ Error: {e}")
            results.append({
                "file": file_path.name,
                "gds_folder": gds_folder,
                "error": str(e)
            })
    
    return results

def main():
    print("🔍 Iniciando prueba de parsers con dataset de muestra...\n")
    
    all_results = []
    
    gds_folders = ["KIU", "SABRE", "COPA", "Amadeus"]
    
    for gds in gds_folders:
        print(f"\n📂 Probando carpeta: {gds}")
        results = test_parser_on_samples(gds, max_samples=3)
        all_results.extend(results)
    
    # Guardar resultados
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Resultados guardados en: {OUTPUT_PATH}")
    
    # Resumen
    print("\n📊 RESUMEN:")
    systems_detected = {}
    for r in all_results:
        if 'detected_system' in r:
            sys = r['detected_system']
            systems_detected[sys] = systems_detected.get(sys, 0) + 1
    
    for sys, count in systems_detected.items():
        print(f"  {sys}: {count} tickets")

if __name__ == "__main__":
    main()

#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script mejorado para probar parsers individuales con muestras específicas.
Genera reporte detallado de cada campo extraído.
"""

import os
import sys
import json
from pathlib import Path
from typing import Dict, Any

# Setup Django
sys.path.insert(0, str(Path(__file__).parent.parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')

import django
django.setup()

from core.parsers.sabre_parser import SabreParser
from core.parsers.amadeus_parser import AmadeusParser
from core.parsers.copa_parser import CopaParser
from core.parsers.kiu_parser import KIUParser
from core.parsers.tk_connect_parser import TKConnectParser
from core.parsers.wingo_parser import WingoParser
from core.parsers.web_receipt_parser import WebReceiptParser

import pdfplumber
from email import policy
from email.parser import BytesParser

DATASET_PATH = r"C:\Users\ARMANDO\Downloads\Boletos"
OUTPUT_PATH = Path(__file__).parent.parent / "parser_detailed_results.json"

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

def test_parser_with_sample(parser, parser_name, file_path):
    """Prueba un parser específico con un archivo"""
    print(f"\n{'='*80}")
    print(f"Parser: {parser_name}")
    print(f"File: {Path(file_path).name}")
    print(f"{'='*80}")
    
    plain_text, html_text = extract_text_from_file(file_path)
    
    if not plain_text:
        print("❌ No se pudo extraer texto")
        return None
    
    # Test detection
    can_parse = parser.can_parse(plain_text)
    print(f"Can Parse: {'✅ YES' if can_parse else '❌ NO'}")
    
    if not can_parse:
        return {
            "file": Path(file_path).name,
            "parser": parser_name,
            "can_parse": False,
            "error": "Parser detection failed"
        }
    
    # Parse
    try:
        result = parser.parse(plain_text, html_text)
        result_dict = result.to_dict()
        
        # Extract key fields for display
        print(f"\n📋 EXTRACTED DATA:")
        print(f"  System: {result_dict.get('SOURCE_SYSTEM')}")
        print(f"  PNR: {result_dict.get('pnr')}")
        print(f"  Ticket #: {result_dict.get('ticket_number')}")
        print(f"  Passenger: {result_dict.get('passenger_name')}")
        print(f"  Airline: {result_dict.get('airline_name')}")
        print(f"  Total: {result_dict.get('total')}")
        print(f"  Flights: {len(result_dict.get('flights', []))}")
        
        # Show first flight details if exists
        if result_dict.get('flights'):
            f = result_dict['flights'][0]
            print(f"\n  ✈️ First Flight:")
            print(f"    Flight #: {f.get('numero_vuelo')}")
            print(f"    Route: {f.get('origen', {}).get('ciudad', 'N/A')} → {f.get('destino', {}).get('ciudad', 'N/A')}")
            print(f"    Date: {f.get('fecha_salida')}")
            print(f"    Time: {f.get('hora_salida')} - {f.get('hora_llegada')}")
        
        return {
            "file": Path(file_path).name,
            "parser": parser_name,
            "can_parse": True,
            "success": True,
            "data": {
                "system": result_dict.get('SOURCE_SYSTEM'),
                "pnr": result_dict.get('pnr'),
                "ticket_number": result_dict.get('ticket_number'),
                "passenger": result_dict.get('passenger_name'),
                "airline": result_dict.get('airline_name'),
                "total": result_dict.get('total'),
                "flights_count": len(result_dict.get('flights', [])),
                "all_keys": list(result_dict.keys())
            }
        }
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return {
            "file": Path(file_path).name,
            "parser": parser_name,
            "can_parse": True,
            "success": False,
            "error": str(e)
        }

def main():
    print("🔍 PRUEBA DETALLADA DE PARSERS\n")
    
    all_results = []
    
    # Test SABRE
    print("\n" + "="*80)
    print("TESTING SABRE PARSER")
    print("="*80)
    sabre_parser = SabreParser()
    sabre_samples = list(Path(DATASET_PATH, "SABRE").glob("*.pdf"))[:3]
    
    for sample in sabre_samples:
        result = test_parser_with_sample(sabre_parser, "SABRE", str(sample))
        if result:
            all_results.append(result)
    
    # Test KIU
    print("\n" + "="*80)
    print("TESTING KIU PARSER")
    print("="*80)
    kiu_parser = KIUParser()
    kiu_samples = list(Path(DATASET_PATH, "KIU").glob("*.eml"))[:3]
    
    for sample in kiu_samples:
        result = test_parser_with_sample(kiu_parser, "KIU", str(sample))
        if result:
            all_results.append(result)
    
    # Test COPA
    print("\n" + "="*80)
    print("TESTING COPA PARSER")
    print("="*80)
    copa_parser = CopaParser()
    copa_samples = list(Path(DATASET_PATH, "COPA").glob("*.pdf"))[:3]
    
    for sample in copa_samples:
        result = test_parser_with_sample(copa_parser, "COPA", str(sample))
        if result:
            all_results.append(result)
    
    # Test AMADEUS
    print("\n" + "="*80)
    print("TESTING AMADEUS PARSER")
    print("="*80)
    amadeus_parser = AmadeusParser()
    amadeus_samples = list(Path(DATASET_PATH, "Amadeus").glob("*.pdf"))[:3]
    
    for sample in amadeus_samples:
        result = test_parser_with_sample(amadeus_parser, "AMADEUS", str(sample))
        if result:
            all_results.append(result)
    
    # Save results
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    
    print(f"\n\n✅ Resultados guardados en: {OUTPUT_PATH}")
    
    # Summary
    print("\n" + "="*80)
    print("📊 RESUMEN FINAL")
    print("="*80)
    
    by_parser = {}
    for r in all_results:
        parser = r['parser']
        if parser not in by_parser:
            by_parser[parser] = {'total': 0, 'success': 0, 'can_parse': 0}
        
        by_parser[parser]['total'] += 1
        if r.get('can_parse'):
            by_parser[parser]['can_parse'] += 1
        if r.get('success'):
            by_parser[parser]['success'] += 1
    
    for parser, stats in by_parser.items():
        print(f"\n{parser}:")
        print(f"  Samples: {stats['total']}")
        print(f"  Detection: {stats['can_parse']}/{stats['total']} ({stats['can_parse']/stats['total']*100:.0f}%)")
        print(f"  Extraction: {stats['success']}/{stats['total']} ({stats['success']/stats['total']*100:.0f}%)")

if __name__ == "__main__":
    main()

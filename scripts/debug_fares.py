
import sys
import os
import json
import pdfplumber
import re

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Set up Django environment
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from core.parsers.sabre_parser import SabreParser

pdf_paths = [
    r"C:\Users\ARMANDO\Downloads\Recibo de pasaje electrónico, 13 febrero para OSCAR DUQUE.pdf",
    r"C:\Users\ARMANDO\Downloads\Recibo de pasaje electrónico, 19 noviembre para ALIKY DE SOUSA.pdf",
    r"C:\Users\ARMANDO\Downloads\Recibo de pasaje electrónico, 26 diciembre para BRIGIDA DEL CARMEN ABREO DURAN.pdf"
]

for pdf_path in pdf_paths:
    print(f"\nProcessing: {pdf_path}")
    if not os.path.exists(pdf_path):
        print(f"File not found: {pdf_path}")
        continue

    text_content = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text_content += (page.extract_text() or "") + "\n"

    print(f"--- TEXT CONTENT START ({len(text_content)} chars) ---")
    
    # Buscar "Detalles De Pago" simple y mostrar contexto
    idx = text_content.find("Detalles De Pago")
    if idx == -1:
        idx = text_content.find("PAYMENT DETAILS")
    
    if idx != -1:
        start = max(0, idx)
        end = min(len(text_content), idx + 1000) # 1000 chars after
    else:
        start = 0
        end = 0

    if pdf_path == pdf_paths[0]:
        with open('debug_full.txt', 'w', encoding='utf-8') as f:
            f.write(text_content)
    
    with open('debug_context.txt', 'a', encoding='utf-8') as f:
        f.write(f"\n--- MATCH FOUND AT {idx} ---\n")
        if idx != -1:
             f.write(text_content[start:end])
        else:
             f.write("NO MATCH FOUND")
        f.write("\n--- END MATCH ---\n")
        # print(f"--- MATCH FOUND AT {idx} ---")
        # print(text_content[start:end])

    print("--- TEXT CONTENT END ---")

    parser = SabreParser()
    result = parser.parse(text_content)
    data = result.to_dict()

    print("\n--- PARSED FARES ---")
    print(json.dumps(data.get('tarifas', {}), indent=2))

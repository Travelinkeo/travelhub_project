import os
import django
import sys
import json
import logging
import time
import email
from email import policy
from bs4 import BeautifulSoup
import re

# Configurar Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from core.parsers.kiu_parser import KIUParser
from core.ticket_parser import generate_ticket
from apps.bookings.models import BoletoImportado

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

INPUT_DIR = r"C:\Users\ARMANDO\Downloads\Boletos\KIU"
OUTPUT_DIR = r"C:\Users\ARMANDO\travelhub_project\KIU_SINGLE_OUTPUT"

def extract_text_from_file(file_path):
    text = ""
    if file_path.lower().endswith('.pdf'):
        import fitz
        try:
            with fitz.open(file_path) as doc:
                for page in doc:
                    text += page.get_text()
        except Exception as e:
            print(f"Error reading PDF: {e}")
    elif file_path.lower().endswith('.eml'):
        try:
            with open(file_path, 'rb') as f:
                msg = email.message_from_binary_file(f, policy=policy.default)
            body = msg.get_body(preferencelist=('html', 'plain'))
            if body:
                content = body.get_content()
                if body.get_content_type() == 'text/html':
                    soup = BeautifulSoup(content, 'html.parser')
                    text = soup.get_text(separator=' ')
                else:
                    text = content
            if not text:
               for part in msg.walk():
                   if part.get_content_type() == 'text/plain':
                       text += part.get_content()
        except Exception as e:
            print(f"Error parsing EML: {e}")
    else:
        try:
             with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                 text = f.read()
        except: pass
    return text

def test_single_file(query):
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    # Find file
    target_file = None
    for f in os.listdir(INPUT_DIR):
        if query.lower() in f.lower():
            target_file = f
            break
    
    if not target_file:
        print(f"❌ Archivo no encontrado con query: {query}")
        return

    print(f"📂 Procesando: {target_file}")
    file_path = os.path.join(INPUT_DIR, target_file)
    text = extract_text_from_file(file_path)
    
    if not text:
        print("❌ No se pudo extraer texto.")
        return

    parser = KIUParser()
    data = parser.parse(text)
    
    print("-" * 40)
    print(f"Pax: {data.passenger_name}")
    print(f"Agente: {data.agency.get('nombre')}")
    print(f"Ref: {data.pnr}")
    print(f"Vuelos: {len(data.flights)}")
    for f in data.flights:
        print(f"  - {f.get('aerolinea')} {f.get('numero_vuelo')} {f.get('origen')}-{f.get('destino')}")
    print("-" * 40)

    # Save validation JSON
    validation_data = {
        "pax": data.passenger_name,
        "agent": data.agency.get('nombre'),
        "pnr": data.pnr
    }
    with open(os.path.join(OUTPUT_DIR, "validation_result.json"), "w") as f:
        json.dump(validation_data, f, indent=2)

    # Generate PDF
    pdf_bytes, filename = generate_ticket(data.to_dict())
    if pdf_bytes:
        out_path = os.path.join(OUTPUT_DIR, f"TEST_{target_file}.pdf")
        with open(out_path, 'wb') as f:
            f.write(pdf_bytes)
        print(f"✅ PDF Generado: {out_path}")
    else:
        print("❌ Error generando PDF")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        test_single_file(sys.argv[1])
    else:
        print("Uso: python scripts/test_kiu_single.py <parte_del_nombre_archivo>")


import os
import sys
import django
import json

# Setup Django
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from core.ticket_parser import extract_data_from_text
import pdfplumber

# Use absolute path to be safe
PDF_PATH = os.path.join(os.getcwd(), "core/tests/fixtures/Recibo_de_pasaje_electrónico_19_marzo_para_ROSANGELA_DIAZ_SILVA_hgbtqy.pdf")

def main():
    print(f"Testing Integration on: {PDF_PATH}")
    
    text = ""
    try:
        with pdfplumber.open(PDF_PATH) as pdf:
            for page in pdf.pages:
                text += (page.extract_text() or "") + "\n"
    except Exception as e:
        print(f"Error reading PDF: {e}")
        return
            
    # This call should now trigger the "🤖 Intentando parseo con IA (Gemini)..." log
    data = extract_data_from_text(text)
    
    print("\n--- RESULTADO INTEGRADO ---")
    print(f"Source System: {data.get('SOURCE_SYSTEM')}")
    print(f"PNR: {data.get('pnr')}")
    print(f"Pasajero: {data.get('pasajero')}")
    print(f"Vuelos: {len(data.get('vuelos', []))}")
    
    if data.get('SOURCE_SYSTEM') == 'GEMINI_AI':
        print("\n✅ ÉXITO: El sistema usó Gemini AI por defecto.")
    else:
        print(f"\n⚠️ PRECAUCIÓN: El sistema usó {data.get('SOURCE_SYSTEM')}")

if __name__ == "__main__":
    main()

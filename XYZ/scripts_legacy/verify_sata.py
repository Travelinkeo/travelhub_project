
import os
import sys
import django
import json

# Setup Django
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from core.parsers.sabre_parser import SabreParser
import pdfplumber

PDF_PATH = r"C:\Users\ARMANDO\Downloads\boletos revision sabre\Recibo_de_pasaje_electrónico_19_marzo_para_ROSANGELA_DIAZ_SILVA_hgbtqy.pdf"

def main():
    print(f"Verifying SATA PDF: {PDF_PATH}")
    
    text = ""
    with pdfplumber.open(PDF_PATH) as pdf:
        for page in pdf.pages:
            text += (page.extract_text() or "") + "\n"
            
    parser = SabreParser()
    data = parser.parse(text)
    
    # Check both 'vuelos' (dict) and 'flights' (object)
    if isinstance(data, dict):
        flights = data.get('vuelos', [])
    else:
        flights = getattr(data, 'flights', []) or getattr(data, 'vuelos', [])
        
    print(f"\n--- FLIGHTS FOUND: {len(flights)} ---")
    for i, f in enumerate(flights):
        print(f"Flight {i+1}: {f.get('aerolinea')} {f.get('numero_vuelo')}")
        print(f"  Fecha Salida:  {f.get('fecha_salida')}")
        print(f"  Origen:  '{f.get('origen', {}).get('ciudad')}'")
        print(f"  Destino: '{f.get('destino', {}).get('ciudad')}'")

if __name__ == "__main__":
    main()

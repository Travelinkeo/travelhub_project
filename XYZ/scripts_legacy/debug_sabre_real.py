
import os
import sys
import django
import json
import re

# Setup Django
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

import pdfplumber
try:
    import pypdf
except ImportError:
    pypdf = None

from core.parsers.sabre_parser import SabreParser

PDF_PATH = r"C:\Users\ARMANDO\Downloads\Recibo de pasaje electrónico, 22 diciembre para KEILIS PIZZANI DE SANTIAGO.pdf"

def extract_text_simulated(path):
    print(f"Reading: {path}")
    text = ""
    # 1. PDFPlumber
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            text += (page.extract_text() or "") + "\n"
    
    # 2. PyPDF Fallback (Same logic as TicketParserService)
    if pypdf:
        try:
            reader = pypdf.PdfReader(path)
            text_pypdf = ""
            for page in reader.pages:
                text_pypdf += (page.extract_text() or "") + "\n"
            
            if text_pypdf:
                text += "\n\n--- FALLBACK EXTRACTION ---\n\n" + text_pypdf
        except Exception as e:
            print(f"PyPDF Error: {e}")
            
    return text

def main():
    if not os.path.exists(PDF_PATH):
        print("File not found.")
        return

    # Extract
    full_text = extract_text_simulated(PDF_PATH)
    
    # Simulate Truncation 
    stop_phrases = [
            "Por favor contacte a su agente de viajes por mas detalles sobre la tarifa",
            "Avisos legales importantes",
            "ADVICE TO INTERNATIONAL PASSENGERS",
            "NOTICE OF BAGGAGE LIABILITY LIMITATIONS"
    ]
    text_debug = full_text
    for phrase in stop_phrases:
        if phrase in text_debug:
            print(f"DEBUG: Splitting by '{phrase}'")
            text_debug = text_debug.split(phrase)[0]
    
    print(f"DEBUG: Text Length After Truncation: {len(text_debug)}")
    
    # Simulate Legacy Parsing Split
    chunks = re.split(r'(?:\n|^)\s*(?:Date|Fecha)\s+', text_debug, flags=re.IGNORECASE)
    print(f"DEBUG: 'Fecha/Date' Chunks found: {len(chunks)}")
    if len(chunks) > 1:
        print(f"DEBUG: Chunk 1 start: {chunks[1][:100]}...")
    else:
        print("DEBUG: No headers found! Dumping text start:")
        print(text_debug[:500])
        
    # Check for Flight Code
    if "AV8396" in text_debug or "AV 8396" in text_debug:
        print("DEBUG: Flight code AV8396 FOUND in text.")
    else:
        print("DEBUG: Flight code AV8396 NOT FOUND in text! Truncation killed it?")

    # Parse
    parser = SabreParser()
    data = parser.parse(full_text) # Use full_text because parse() does truncation internally now.
    
    print("\n--- RAW OUTPUT (SUPPRESSED) ---")
    # print(data)
    
    # Verify specific fields
    print("\n--- VERIFICACION ---")
    pnr = data.get('pnr') if isinstance(data, dict) else getattr(data, 'pnr', 'N/A')
    print(f"PNR Global: {pnr}")
    
    # Check both 'vuelos' (dict) and 'flights' (object)
    if isinstance(data, dict):
        flights = data.get('vuelos', [])
    else:
        flights = getattr(data, 'flights', []) or getattr(data, 'vuelos', [])
        
    print(f"Vuelos encontrados: {len(flights)}")
    for f in flights:
        # Handle dict or obj
        def get_val(obj, key):
            return obj.get(key) if isinstance(obj, dict) else getattr(obj, key, None)
            
        aerolinea = get_val(f, 'aerolinea')
        num = get_val(f, 'numero_vuelo')
        
        orig = get_val(f, 'origen')
        dest = get_val(f, 'destino')
        c_orig = (orig.get('ciudad') if isinstance(orig, dict) else getattr(orig, 'ciudad', orig)) if orig else '?'
        c_dest = (dest.get('ciudad') if isinstance(dest, dict) else getattr(dest, 'ciudad', dest)) if dest else '?'
        
        eq = get_val(f, 'equipaje')
        pnr_loc = get_val(f, 'codigo_reservacion_local')

        print(f" - {aerolinea} {num}: {c_orig} -> {c_dest}")
        print(f"   Equipaje: {eq} | PNR Local: {pnr_loc}")

if __name__ == "__main__":
    main()

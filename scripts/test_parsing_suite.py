import os
import sys
import django
import glob
import email
import pdfplumber
import re
from bs4 import BeautifulSoup

# Setup Django
sys.path.append('c:\\Users\\ARMANDO\\travelhub_project')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from core.ticket_parser import extract_data_from_text, _parse_kiu_ticket

DATASET_DIR = r"c:\Users\ARMANDO\travelhub_project\core\tests\dataset"

def extract_text_from_eml(file_path):
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        msg = email.message_from_file(f)
        
    body = ""
    html_content = ""
    for part in msg.walk():
        if part.get_content_type() == 'text/plain':
            body += part.get_payload(decode=True).decode('utf-8', errors='ignore')
        elif part.get_content_type() == 'text/html':
            html_content += part.get_payload(decode=True).decode('utf-8', errors='ignore')
            
    if html_content:
        soup = BeautifulSoup(html_content, 'html.parser')
        return soup.get_text(separator=' '), html_content
    return body, ""

def extract_text_from_pdf(file_path):
    text = ""
    try:
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text += (page.extract_text() or "") + "\n"
    except Exception as e:
        print(f"Error reading PDF {file_path}: {e}")
    return text, ""

def run_debug():
    # Pick a few representative files
    target_files = [ 
        "Gmail - E-TICKET ITINERARY RECEIPT - MURILLO CORTES_DIANA PATRICIA.pdf"
    ]
    
    files = glob.glob(os.path.join(DATASET_DIR, "*"))
    
    print(f"--- DEBUGGING {len(target_files)} FILES ---")
    
    for filename in target_files:
        print(f"\n==========================================")
        print(f"File: {filename}")
        file_path = os.path.join(DATASET_DIR, filename)
        if not os.path.exists(file_path):
            print("File not found in dataset dir (might depend on copy result).")
            # Try to partial match
            matches = [f for f in files if filename in os.path.basename(f)]
            if matches:
                file_path = matches[0]
                print(f"Found match: {file_path}")
            else:
                continue

        ext = os.path.splitext(file_path)[1].lower()
        plain_text = ""
        html_text = ""
        
        if ext == '.eml':
            plain_text, html_text = extract_text_from_eml(file_path)
            print("Type: EML")
        elif ext == '.pdf':
            plain_text, html_text = extract_text_from_pdf(file_path)
            print("Type: PDF")
            
        print(f"Text Length: {len(plain_text)}")
        print(f"Snippet (First 1500 chars): \n{plain_text[:1500]}")
        
        # Check KIU Detection Logic
        plain_text_upper = plain_text.upper()
        is_kiu = 'KIUSYS.COM' in plain_text_upper or \
             'PASSENGER ITINERARY RECEIPT' in plain_text_upper or \
             ('ISSUE AGENT' in plain_text_upper and 'FROM/TO' in plain_text_upper) or \
             'AVIOR AIRLINES' in plain_text_upper 
             
        print(f"Detected as KIU? {is_kiu}")
        
        # Run Parser
        try:
            parsed_data = extract_data_from_text(plain_text, html_text, pdf_path=file_path)
            
            print(f"Source System: {parsed_data.get('SOURCE_SYSTEM')}")
            print(f"Passenger: {parsed_data.get('NOMBRE_DEL_PASAJERO')}")
            
            vuelos = parsed_data.get('vuelos', [])
            print(f"Flights Count: {len(vuelos)}")
            for i, v in enumerate(vuelos):
                print(f"  [{i}] {v.get('fecha')} {v.get('aerolinea')} {v.get('numero_vuelo')} {v.get('origen')}-{v.get('destino')}")
                
            print(f"Raw Itinerary: {str(parsed_data.get('ItinerarioFinalLimpio'))[:200]}...")
            
        except Exception as e:
            print(f"EXCEPTION: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    run_debug()

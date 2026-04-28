import sys
import os
import django
import email
from email import policy
import glob

# Setup Django
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from core.parsers.kiu_parser import KIUParser
from bs4 import BeautifulSoup

def extract_body(eml_path):
    with open(eml_path, 'rb') as f:
        msg = email.message_from_binary_file(f, policy=policy.default)
    
    body = ""
    html_body = ""
    
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            cdispo = str(part.get('Content-Disposition'))
            
            if ctype == 'text/plain' and 'attachment' not in cdispo:
                try:
                    body += part.get_content()
                except: pass
            elif ctype == 'text/html' and 'attachment' not in cdispo:
                try:
                    html_content = part.get_content()
                    html_body += html_content
                    # Fallback text extract from HTML
                    soup = BeautifulSoup(html_content, 'html.parser')
                    body += soup.get_text(separator='\n')
                except: pass
    else:
        try:
            body = msg.get_content()
        except: pass
        
    return body

def analyze_tickets():
    files = [
        r"C:\Users\ARMANDO\Downloads\E-TICKET ITINERARY RECEIPT - DUQUE ECHEVERRY_CRISTIAN DAVID (1).eml",
        r"C:\Users\ARMANDO\Downloads\E-TICKET ITINERARY RECEIPT - GIRALDO GARCIA_INGRID ALEJANDRA (1).eml",
        r"C:\Users\ARMANDO\Downloads\E-TICKET ITINERARY RECEIPT - GIRALDO GARCIA_INGRID ALEJANDRA.eml",
        r"C:\Users\ARMANDO\Downloads\E-TICKET ITINERARY RECEIPT - GOMEZ ZULUAGA_SERGIO IVAN.eml",
        r"C:\Users\ARMANDO\Downloads\E-TICKET ITINERARY RECEIPT - DUQUE ECHEVERRY_CRISTIAN DAVID (2).eml"
    ]
    
    parser = KIUParser()
    
    print(f"--- ANALYZING {len(files)} EML FILES ---")
    
    for fpath in files:
        print(f"\nProcessing: {os.path.basename(fpath)}")
        if not os.path.exists(fpath):
            print(" [ERROR] File not found.")
            continue
            
        try:
            text = extract_body(fpath)
            # print(f"DEBUG TEXT LEN: {len(text)}")
            
            parsed = parser.parse(text)
            
            print(f"  > System: {parsed.source_system}")
            print(f"  > PNR: {parsed.pnr}")
            print(f"  > Passenger: {parsed.passenger_name}")
            print(f"  > Flights: {len(parsed.flights)}")
            
            if not parsed.flights:
                 print("    [FAIL] No flights found!")
                 # Print snippet to debug regex
                 print("    --- TEXT SNIPPET (First 20 lines) ---")
                 print('\n'.join(text.splitlines()[:20]))
                 print("    --- FLIGHT SECTION SEARCH ---")
                 # Try to find standard keywords
                 import re
                 match = re.search(r'(FROM/TO|DESDE/HACIA)', text, re.IGNORECASE)
                 if match:
                     start = match.start()
                     print(text[start:start+500])
                 else:
                     print("    [FAIL] Could not find FROM/TO section.")
            else:
                 for f in parsed.flights:
                     print(f"    - {f['aerolinea']} {f['numero_vuelo']} {f['origen']}->{f['destino']} ({f['fecha']})")

        except Exception as e:
            print(f"  [CRASH] {e}")

if __name__ == '__main__':
    analyze_tickets()

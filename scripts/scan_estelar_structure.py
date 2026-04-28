import sys
import os
import django
import email
from email import policy
import re
from bs4 import BeautifulSoup

# Setup Django (Just for env context if needed)
sys.path.append(os.getcwd())
# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')

def extract_body(eml_path):
    with open(eml_path, 'rb') as f:
        msg = email.message_from_binary_file(f, policy=policy.default)
    
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            if ctype == 'text/plain':
                try: body += part.get_content()
                except: pass
            elif ctype == 'text/html':
                try:
                    html_content = part.get_content()
                    soup = BeautifulSoup(html_content, 'html.parser')
                    body += soup.get_text(separator='\n')
                except: pass
    else:
        try: body = msg.get_content()
        except: pass
    return body

def scan_tickets():
    files = [
        r"C:\Users\ARMANDO\Downloads\E-TICKET ITINERARY RECEIPT - DUQUE ECHEVERRY_CRISTIAN DAVID (1).eml",
        r"C:\Users\ARMANDO\Downloads\E-TICKET ITINERARY RECEIPT - GIRALDO GARCIA_INGRID ALEJANDRA (1).eml"
    ]
    
    print("--- SCANNING ESTELAR/KIU STRUCTURE ---")
    
    for fpath in files:
        if not os.path.exists(fpath): continue
        print(f"\nProcessing: {os.path.basename(fpath)}")
        
        text = extract_body(fpath)
        lines = text.splitlines()
        
        # Look for the Flight Header
        header_idx = -1
        for i, line in enumerate(lines):
            if re.search(r'(FROM/TO|DESDE/HACIA|FLIGHT|VUELO)', line, re.IGNORECASE):
                # Print context around header
                print("\n[HEADER CONTEXT]")
                for j in range(max(0, i-2), min(len(lines), i+15)):
                    print(f"{j}: {lines[j].strip()}")
                break
        
        # Look for Flight Patterns (ES followed by numbers)
        print("\n[POTENTIAL FLIGHT LINES]")
        for i, line in enumerate(lines):
            # Matches standard 2-char code + number (e.g. ES 791, ES791)
            if re.search(r'\b[A-Z0-9]{2}\s?\d{3,4}\b', line):
                 print(f"{i}: {line.strip()}")

if __name__ == '__main__':
    scan_tickets()

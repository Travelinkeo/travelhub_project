import sys
import os
import logging
from pathlib import Path
from email import policy
from email.parser import BytesParser
from bs4 import BeautifulSoup
import re

# Setup Django environment
sys.path.append(str(Path.cwd()))
# Force UTF-8
sys.stdout.reconfigure(encoding='utf-8')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
import django
django.setup()

from core.parsers.web_receipt_parser import WebReceiptParser

eml_path = r"C:\Users\ARMANDO\Downloads\Fwd_ Tickets Avior Airlines.eml"

print(f"Reading file: {eml_path}")

with open(eml_path, 'rb') as f:
    msg = BytesParser(policy=policy.default).parse(f)

html_content = ""
text_content = ""

if msg.is_multipart():
    for part in msg.walk():
        ctype = part.get_content_type()
        if ctype == 'text/html':
            html_content += part.get_content()
        elif ctype == 'text/plain':
            text_content += part.get_content()
else:
    html_content = msg.get_content()

if not html_content and text_content:
    # Use text content if HTML is missing
    html_content = f"<html><body><pre>{text_content}</pre></body></html>"

# Write to file
with open('debug_result_clean.txt', 'w', encoding='utf-8') as f:
    f.write(f"Content Size: {len(html_content)} bytes\n\n")
    
    # Run Parser
    parser = WebReceiptParser()
    result = parser.parse(html_content)

    f.write("\n--- PARSER RESULT STRUCTURE ---\n")
    if isinstance(result, dict):
        f.write(f"Keys: {result.keys()}\n")
        if 'tickets' in result:
            f.write(f"Ticket Count: {len(result['tickets'])}\n")
            for i, t in enumerate(result['tickets']):
                f.write(f"  Ticket {i+1}: {t.get('NOMBRE_DEL_PASAJERO')} - {t.get('NUMERO_DE_BOLETO')}\n")
                if 'vuelos' in t and t['vuelos']:
                    v = t['vuelos'][0]
                    f.write(f"    Vuelo: {v.get('origen')} -> {v.get('destino')}\n")
    else:
        f.write(f"Result type: {type(result)}\n")

    # Debug Destination
    soup = BeautifulSoup(html_content, 'html.parser')
    text = soup.get_text()

    f.write("\n--- TEXT AROUND 'Información del viaje' (Destination Debug) ---\n")
    # Search logic ...
    matches = [m.start() for m in re.finditer(r'Informaci.n del viaje', text, re.IGNORECASE)]
    if not matches:
        matches = [m.start() for m in re.finditer(r'(?:Salida|Llegada|Origen|Destino)', text, re.IGNORECASE)]

    for idx in matches[:5]: 
        start = max(0, idx - 100)
        end = min(len(text), idx + 300)
        snippet = text[start:end].replace('\n', '[NL]')
        f.write(f"\nCONTEXT ({idx}):\n{snippet}\n")
    
    f.write("\n--- TEXT AROUND '742' (Ticket Debug) ---\n")
    tkt_matches = [m.start() for m in re.finditer(r'742\d{10}', text)]
    for idx in tkt_matches:
        start = max(0, idx - 50)
        end = min(len(text), idx + 100)
        snippet = text[start:end].replace('\n', '[NL]')
        f.write(f"\nCONTEXT ({idx}):\n{snippet}\n")

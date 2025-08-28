import os
import email
from email import policy
from bs4 import BeautifulSoup
import json
import re
import sys

# Asegurar raíz en sys.path
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from external_ticket_generator.KIU.mi_proyecto_final.mi_proyecto_final.main import extract_data_from_text

BASE_DIR = os.path.join(ROOT, 'external_ticket_generator', 'KIU')
# Patrones de archivos relevantes (varían un poco los nombres con sufijo 1)
TARGET_PATTERNS = [
    'E-TICKET ITINERARY RECEIPT - DUQUE ECHEVERRY_OSCAR HUMBERTO.eml',
    'E-TICKET ITINERARY RECEIPT - DUQUE ECHEVERRY_OSCAR HUMBERTO1.eml'
]

def load_eml(path: str):
    with open(path, 'rb') as f:
        msg = email.message_from_binary_file(f, policy=policy.default)
    html_body = ''
    plain_text = ''
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            cdisp = str(part.get('Content-Disposition'))
            if 'attachment' in cdisp:
                continue
            charset = part.get_content_charset() or 'utf-8'
            payload = part.get_payload(decode=True)
            if not payload:
                continue
            try:
                decoded = payload.decode(charset, errors='ignore')
            except Exception:
                decoded = payload.decode('utf-8', errors='ignore')
            if ctype == 'text/html':
                html_body = decoded
            elif ctype == 'text/plain':
                plain_text = decoded
    else:
        charset = msg.get_content_charset() or 'utf-8'
        payload = msg.get_payload(decode=True)
        if payload:
            decoded = payload.decode(charset, errors='ignore')
            if msg.get_content_type() == 'text/html':
                html_body = decoded
            else:
                plain_text = decoded
    if not plain_text and html_body:
        plain_text = BeautifulSoup(html_body, 'html.parser').get_text('\n')
    return plain_text, html_body


def main():
    print("=== Prueba de parseo para EML de DUQUE ECHEVERRY / OSCAR HUMBERTO ===")
    for fname in TARGET_PATTERNS:
        path = os.path.join(BASE_DIR, fname)
        if not os.path.exists(path):
            print(f"[WARN] No encontrado: {fname}")
            continue
        print(f"\nProcesando: {fname}")
        plain_text, html_text = load_eml(path)
        if not plain_text.strip():
            print("[ERROR] No se obtuvo texto plano utilizable")
            continue
        parsed = extract_data_from_text(plain_text, html_text)
        print("Nombre pasajero bruto final:", parsed.get('NOMBRE_DEL_PASAJERO'))
        print("Solo nombre pasajero:", parsed.get('SOLO_NOMBRE_PASAJERO'))
        print("JSON completo:")
        print(json.dumps(parsed, indent=2, ensure_ascii=False))

if __name__ == '__main__':
    main()

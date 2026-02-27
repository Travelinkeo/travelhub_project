import email
from email import policy
import os
import sys
import django
import json
from dotenv import load_dotenv

load_dotenv()
os.environ["GEMINI_API_KEY"] = "AIzaSyBsQWW6Yz_Hd3vAYKK5sV7W_vZz4jffkVM"

sys.path.append(r'c:\Users\ARMANDO\travelhub_project')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from core.ticket_parser import extract_data_from_text

def test_file(path):
    print(f"\n--- TESTING: {os.path.basename(path)} ---")
    if not os.path.exists(path):
        print(f"FILE NOT FOUND: {path}")
        return

    plain_text = ""
    if path.endswith('.eml'):
        with open(path, 'rb') as f:
            msg = email.message_from_binary_file(f, policy=policy.default)
        body = msg.get_body(preferencelist=('plain',))
        plain_text = body.get_content() if body else ""
    else:
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            plain_text = f.read()

    print(f"DEBUG: Processing {len(plain_text)} chars...")
    data = extract_data_from_text(plain_text, "")
    print(f"SOURCE: {data.get('SOURCE_SYSTEM')}")
    print(f"PASSENGER: {data.get('NOMBRE_DEL_PASAJERO')}")
    print(f"PNR: {data.get('CODIGO_RESERVA')}")
    print(f"FLIGHTS: {len(data.get('vuelos', []))} segments")
    for i, v in enumerate(data.get('vuelos', []), 1):
        print(f"   [{i}] {v.get('aerolinea')} {v.get('numero_vuelo')}: {v.get('origen')} -> {v.get('destino')} ({v.get('fecha_salida')})")
    print(f"TOTAL: {data.get('TOTAL')}")

kiu_data = r'C:\Users\ARMANDO\travelhub_project\kiu_extraction.txt'
sabre_eml = r'C:\Users\ARMANDO\travelhub_project\media\boletos_importados\2026\02\ZULUAGA_RIVILLAS_DIEGO_FERNANDO_MR_04MAY2025_CCS_IST.eml'

if __name__ == "__main__":
    test_file(sabre_eml)
    test_file(kiu_data)

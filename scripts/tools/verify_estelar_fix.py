import sys
import os

# Añadir el path del proyecto para importar los módulos de Django
sys.path.append(os.getcwd())

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from core.parsers.web_receipt_parser import WebReceiptParser
from bs4 import BeautifulSoup
import json

def test_estelar_fix():
    print("Testing Estelar Fix...")
    parser = WebReceiptParser()
    
    with open("estelar_debug.html", "r", encoding="utf-8") as f:
        html_content = f.read()
    
    soup = BeautifulSoup(html_content, "html.parser")
    
    # Simular la detección de Estelar
    try:
        data = parser._parse_estelar(soup)
        print("\nExtracted Data:")
        print(json.dumps(data, indent=2, ensure_ascii=False, default=str))
        
        if 'error' in data:
            print(f"FAILED: {data['error']}")
            return
            
        tickets = data.get('tickets', [])
        if not tickets:
            print("FAILED: No tickets found")
            return
            
        t = tickets[0]
        # Validar campos clave del EML de prueba
        expected_tkt = "0520270655814"
        expected_pax = "JIMENEZ GIRALDO/JADER ALBERTO"
        expected_pnr = "VYAHKY"
        
        if t['NUMERO_DE_BOLETO'] == expected_tkt and t['NOMBRE_DEL_PASAJERO'] == expected_pax and t['CODIGO_RESERVA'] == expected_pnr:
            print("\nSUCCESS: All key fields extracted correctly!")
        else:
            print("\nPARTIAL SUCCESS/FAILURE: Some fields mismatch.")
            if t['NUMERO_DE_BOLETO'] != expected_tkt: print(f"Ticket mismatch: Got {t['NUMERO_DE_BOLETO']}, Expected {expected_tkt}")
            if t['NOMBRE_DEL_PASAJERO'] != expected_pax: print(f"Pax mismatch: Got {t['NOMBRE_DEL_PASAJERO']}, Expected {expected_pax}")
            if t['CODIGO_RESERVA'] != expected_pnr: print(f"PNR mismatch: Got {t['CODIGO_RESERVA']}, Expected {expected_pnr}")

    except Exception as e:
        print(f"CRASHED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_estelar_fix()

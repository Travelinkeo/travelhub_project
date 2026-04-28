import json
import sys
import os
import django
from datetime import datetime

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from core.parsers.sabre_parser import SabreParser

def test_json_output():
    # Simulated text based on 11 Marzo PDF structure and "Shanghai" case
    raw_text = """
    Información De Vuelo
    
    Salida: 11 mar 26
    China Eastern
    MU710
    MADRID, SPAIN
    SHANGHAI PUDONG,
    CHINA
    PNR: MG8P1N
    10:30
    06:20
    Cabina: TURISTA
    Status: CONFIRMADO
    
    Salida: 24 mar 26
    China Eastern
    MU569
    SHANGHAI PUDONG,
    CHINA
    PARIS DE GAULLE,
    FRANCE
    PNR: MG8P1N
    12:25
    18:05
    Cabina: TURISTA
    
    Detalles De Pago
    """
    
    print("--- SIMULATED RAW TEXT INPUT ---")
    print(raw_text)
    print("--------------------------------")
    
    parser = SabreParser()
    try:
        parsed_data = parser.parse(raw_text)
        
        # Construct a dictionary to dump as JSON
        output = {
            "pnr": parsed_data.pnr,
            "passenger": parsed_data.passenger_name,
            "flights": parsed_data.flights
        }
        
        # Print valid JSON
        json_output = json.dumps(output, indent=4, ensure_ascii=False)
        print("\n--- JSON OUTPUT ---")
        print(json_output)
        print("-------------------")
        
    except Exception as e:
        print(f"Error parsing: {e}")

if __name__ == "__main__":
    test_json_output()

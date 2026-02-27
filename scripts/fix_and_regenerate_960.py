
import os
import sys
import django
from django.conf import settings
import json
import traceback

# Setup Django
sys.path.append('c:\\Users\\ARMANDO\\travelhub_project')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from core.models import BoletoImportado
from core import ticket_parser 

def fix_iata_files():
    print("DEBUG: Fixing IATA JSON files...")
    # ... (Keep IATA fix logic or assume it is done. I'll include it for safety)
    base_dir = os.path.dirname(os.path.abspath(ticket_parser.__file__))
    try:
        # Airlines
        airlines_path = os.path.join(base_dir, 'data', 'airlines.json')
        with open(airlines_path, 'w', encoding='utf-8') as f:
            json.dump({
                "AV": "Avianca",
                "QL": "Laser Airlines",
                "9V": "Avior Airlines",
                "R7": "Aserca Airlines",
                "V0": "Conviasa",
                "ES": "Estelar",
                "5R": "Rutaca",
                "J7": "Afrijet",
                "CM": "Copa Airlines",
                "AA": "American Airlines",
                "UX": "Air Europa",
                "IB": "Iberia"
            }, f, indent=4)
        
        # Airports (City Names Only per user request)
        airports_path = os.path.join(base_dir, 'data', 'airports.json')
        with open(airports_path, 'w', encoding='utf-8') as f:
            json.dump({
                "CCS": "Caracas",
                "MIA": "Miami",
                "MAD": "Madrid",
                "BOG": "Bogota",
                "PTY": "Panama City",
                "SDQ": "Santo Domingo",
                "VLN": "Valencia",
                "MAR": "Maracaibo",
                "PBL": "Puerto Cabello",
                "BRM": "Barquisimeto",
                "PMV": "Porlamar",
                "BLA": "Barcelona",
                "PZO": "Puerto Ordaz",
                "STD": "Santo Domingo (Tachira)",
                "CUN": "Cancun",
                "MEX": "Mexico City",
                "EZE": "Buenos Aires",
                "GRU": "Sao Paulo",
                "LIM": "Lima",
                "SCL": "Santiago de Chile",
                "JFK": "New York",
                "LHR": "London",
                "CDG": "Paris",
                "IST": "Istanbul",
                "DXB": "Dubai",
                "DOH": "Doha",
                "CUR": "Curacao",
                "AUA": "Oranjestad",
                "BON": "Kralendijk"
            }, f, indent=4)
            
        print("DEBUG: IATA files fixed.")
    except Exception as e:
        print(f"DEBUG: Error fixing IATA files: {e}")

def run():
    print("DEBUG: STARTING SCRIPT")
    fix_iata_files()
    
    html_path = r"c:\Users\ARMANDO\travelhub_project\media\boletos_importados\2026\02\email_ticket_b1228_IpZ0Soi.html"
    if not os.path.exists(html_path):
        print(f"DEBUG: HTML file not found: {html_path}")
        return

    print(f"DEBUG: Reading HTML from: {html_path}")
    with open(html_path, 'r', encoding='utf-8') as f:
        html_content = f.read()

    # Extract text (simple fallback if parser doesn't do it)
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html_content, 'html.parser')
    plain_text = soup.get_text(separator='\n')

    print("DEBUG: Running ticket_parser.extract_data_from_text...")
    try:
        data = ticket_parser.extract_data_from_text(plain_text, html_text=html_content)
        print("DEBUG: EXTRACTED DATA DONE")
        print("--- JSON START ---")
        print(json.dumps(data, indent=2, ensure_ascii=False))
        print("--- JSON END ---")
        
        print("DEBUG: Calling generate_ticket...")
        pdf_bytes, filename = ticket_parser.generate_ticket(data)
        
        if pdf_bytes is None:
            print("DEBUG: generate_ticket returned None for bytes!")
        else:
            print(f"DEBUG: Generated {len(pdf_bytes)} bytes. Filename: {filename}")
        
        output_path = os.path.join(r"c:\Users\ARMANDO\travelhub_project", filename)
        print(f"DEBUG: Saving to {output_path}")
        with open(output_path, 'wb') as f:
            f.write(pdf_bytes)
        
        print(f"DEBUG: SAVED SUCCESSFULLY: {output_path}")

        # Update Boleto 960 (Optional simulation)
        try:
            print("DEBUG: Updating DB for Boleto 960")
            boleto = BoletoImportado.objects.get(id=960)
            boleto.datos_parseados = data
            boleto.save(update_fields=['datos_parseados'])
            print("DEBUG: Boleto 960 updated.")
        except BoletoImportado.DoesNotExist:
            print("DEBUG: Boleto 960 not found (skipped DB update).")

    except Exception as e:
        print("DEBUG: EXCEPTION CAUGHT")
        traceback.print_exc()

if __name__ == "__main__":
    run()

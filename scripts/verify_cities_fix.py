
import sys
import os
import json
import pdfplumber

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Set up Django environment
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from core.parsers.sabre_parser import SabreParser

pdf_path = r"c:\Users\ARMANDO\travelhub_project\media\boletos_importados\2026\01\Recibo_de_pasaje_electrónico_07_abril_para_ALEXANDER_CASTANO_VALENCIA.pdf"

if not os.path.exists(pdf_path):
    print(f"File not found: {pdf_path}")
    sys.exit(1)

text_content = ""
with pdfplumber.open(pdf_path) as pdf:
    for page in pdf.pages:
        text_content += (page.extract_text() or "") + "\n"

parser = SabreParser()
result = parser.parse(text_content)
data = result.to_dict()

# Print only relevant parts to verify
print("Flights Summary:")
for i, f in enumerate(data.get('vuelos', [])):
    print(f"Flight {i+1}: {f.get('numero_vuelo')}")
    print(f"  Origin: {f.get('origen', {}).get('ciudad')} ({f.get('origen', {}).get('pais')})")
    print(f"  Dest: {f.get('destino', {}).get('ciudad')} ({f.get('destino', {}).get('pais')})")
    print("-" * 20)

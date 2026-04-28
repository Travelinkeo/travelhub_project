
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

pdf_path = r"c:\Users\ARMANDO\travelhub_project\media\boletos_importados\2026\01\Recibo_de_pasaje_electrónico_21_diciembre_para_LAURA_CRISTINA_ARROYAVE.pdf"

if not os.path.exists(pdf_path):
    print(f"File not found: {pdf_path}")
    sys.exit(1)

text_content = ""
with pdfplumber.open(pdf_path) as pdf:
    for page in pdf.pages:
        text_content += (page.extract_text() or "") + "\n"

print(f"--- TEXT CONTENT START ({len(text_content)} chars) ---")
print(text_content)
print("--- TEXT CONTENT END ---")

parser = SabreParser()
result = parser.parse(text_content)
data = result.to_dict()

print("\n--- PARSED DATA ---")
print(json.dumps(data, indent=2, default=str))

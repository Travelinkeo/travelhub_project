
import sys
import os
import django
from django.conf import settings

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from core.ticket_parser import extract_data_from_text, generate_ticket
import pdfplumber

pdf_path = r"c:\Users\ARMANDO\travelhub_project\media\boletos_importados\2026\01\Recibo_de_pasaje_electrónico_21_diciembre_para_LAURA_CRISTINA_ARROYAVE.pdf"
output_pdf_path = r"c:\Users\ARMANDO\travelhub_project\laura_verification.pdf"

if not os.path.exists(pdf_path):
    print(f"File not found: {pdf_path}")
    sys.exit(1)

print("Extracting text...")
text_content = ""
with pdfplumber.open(pdf_path) as pdf:
    for page in pdf.pages:
        text_content += (page.extract_text() or "") + "\n"

print("Parsing data...")
data = extract_data_from_text(text_content, "SABRE") # Force Sabre parser or let detection work

print(f"Flights found: {len(data.get('flights', []))}")
print(f"Passenger name: {data.get('passenger_name')}")
for i, f in enumerate(data.get('flights', [])):
    print(f"Flight {i+1}: {f.get('numero_vuelo')} - PNR: {f.get('codigo_reservacion_local')}")

print("Generating PDF...")
pdf_bytes, pdf_filename = generate_ticket(data)

with open(output_pdf_path, 'wb') as f:
    f.write(pdf_bytes)

print(f"PDF generated at: {output_pdf_path}")
print(f"Internal filename: {pdf_filename}")

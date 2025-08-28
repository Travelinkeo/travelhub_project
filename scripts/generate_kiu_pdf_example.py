import os, sys, json
from pathlib import Path

# Asegurar path del proyecto
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')

import django
try:
    django.setup()
except Exception as e:
    print(f"Advertencia al inicializar Django (puede no ser necesario para solo generar PDF): {e}")

from core.ticket_parser import extract_data_from_text, generate_ticket
from email import policy
from email.parser import BytesParser

# Ruta del EML de ejemplo (ajusta si quieres otro)
EML_DIR = BASE_DIR / 'external_ticket_generator'
# Seleccionar el primer .eml KIU disponible
candidate = None
for name in os.listdir(EML_DIR):
    if name.lower().endswith('.eml') and 'E-TICKET_ITINERARY_RECEIPT' in name.upper():
        candidate = EML_DIR / name
        break
if not candidate:
    print('No se encontró un .eml de ejemplo en external_ticket_generator')
    raise SystemExit(1)

with open(candidate, 'rb') as f:
    msg = BytesParser(policy=policy.default).parse(f)

plain = msg.get_body(preferencelist=('plain',))
html = msg.get_body(preferencelist=('html',))
plain_text = plain.get_content() if plain else msg.get_content()
html_text = html.get_content() if html else ''

print(f'Usando archivo: {candidate.name}')

# Parsear
parsed = extract_data_from_text(plain_text, html_text)
print('Datos parseados:')
print(json.dumps(parsed, indent=2, ensure_ascii=False))

# Generar PDF
pdf_bytes, filename = generate_ticket(parsed)
output_dir = BASE_DIR / 'media' / 'boletos_generados'
output_dir.mkdir(parents=True, exist_ok=True)
output_path = output_dir / filename
with open(output_path, 'wb') as f:
    f.write(pdf_bytes)
print(f'PDF generado en: {output_path}')

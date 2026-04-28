
import sys
import os
import json

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Set up Django environment
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from core.parsers.sabre_parser import SabreParser
from core.ticket_parser import generate_ticket

# Use the extracted text
text_file = "alexander_text_utf8.txt"
with open(text_file, "r", encoding="utf-8") as f:
    text_content = f.read()

parser = SabreParser()
result = parser.parse(text_content)
data = result.to_dict()

print("Generating PDF...")
try:
    pdf_bytes, filename = generate_ticket(data)
    if pdf_bytes:
        print(f"Success! PDF generated: {filename} ({len(pdf_bytes)} bytes)")
        with open(filename, "wb") as f:
            f.write(pdf_bytes)
    else:
        print(f"Failed! generate_ticket returned empty bytes. Filename: {filename}")
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()

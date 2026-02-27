
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

# Use the extracted text
text_file = "aliky_text_utf8.txt"
if not os.path.exists(text_file):
    print(f"File not found: {text_file}")
    sys.exit(1)

with open(text_file, "r", encoding="utf-8") as f:
    text_content = f.read()

parser = SabreParser()
result = parser.parse(text_content)

print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))

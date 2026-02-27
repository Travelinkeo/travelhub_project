import sys
import os
import logging
from pathlib import Path
from email import policy
from email.parser import BytesParser
from bs4 import BeautifulSoup

# Setup Django environment
sys.path.append(str(Path.cwd()))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
import django
django.setup()

from core.parsers.web_receipt_parser import WebReceiptParser

# File path from user
eml_path = r"C:\Users\ARMANDO\Downloads\Fwd_ Tickets Avior Airlines.eml"

print(f"Reading file: {eml_path}")

if not os.path.exists(eml_path):
    print("❌ File not found! Please check path.")
    sys.exit(1)

with open(eml_path, 'rb') as f:
    msg = BytesParser(policy=policy.default).parse(f)

# Extract HTML/Text
html_content = ""
text_content = ""

if msg.is_multipart():
    for part in msg.walk():
        ctype = part.get_content_type()
        print(f"Part: {ctype}")
        if ctype == 'text/html':
            html_content += part.get_content()
        elif ctype == 'text/plain':
            text_content += part.get_content()
else:
    html_content = msg.get_content()

if not html_content and text_content:
    html_content = f"<html><body><pre>{text_content}</pre></body></html>"

print(f"\nHTML Content extracted: {len(html_content)} chars")

# Run Parser
parser = WebReceiptParser()
print("\n--- Running Parser ---")
result = parser.parse(html_content)

print("\n--- Result ---")
print(result)

# Debug Text Content for Total
soup = BeautifulSoup(html_content, 'html.parser')
text = soup.get_text() # Default separator

print("\n--- Substring around 'TOTAL' ---")
import re
# Check specific matches
total_matches = [m.start() for m in re.finditer(r'(?i)TOTAL', text)]
for idx in total_matches:
    start = max(0, idx - 100)
    end = min(len(text), idx + 300)
    print(f"\nCONTEXT ({idx}):")
    clean_snippet = text[start:end].replace('\n', '[NL]').replace('\r', '[CR]')
    print(clean_snippet)


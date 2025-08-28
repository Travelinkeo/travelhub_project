from email import policy
from email.parser import BytesParser
from pathlib import Path
import json, sys
import os

# Asegurar que la raíz del proyecto esté en sys.path para importar 'core'
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core import ticket_parser

p = Path('external_ticket_generator/KIU/E-TICKET ITINERARY RECEIPT - DUQUE ECHEVERRY_OSCAR HUMBERTO1.eml')
raw = p.read_bytes()
msg = BytesParser(policy=policy.default).parsebytes(raw)
plain, html = '', ''
if msg.is_multipart():
    for part in msg.walk():
        ctype = part.get_content_type()
        if ctype == 'text/plain' and not plain:
            plain = part.get_content()
        elif ctype == 'text/html' and not html:
            html = part.get_content()
else:
    if msg.get_content_type() == 'text/plain':
        plain = msg.get_content()
    elif msg.get_content_type() == 'text/html':
        html = msg.get_content()

print('--- Plain text head ---')
print(plain[:1000])
print('--- HTML head ---')
print((html or '')[:1000])
res = ticket_parser.extract_data_from_text(plain, html)
print('\n--- PARSER RESULT ---')
print(json.dumps(res, indent=2, ensure_ascii=False))

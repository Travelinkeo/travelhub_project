import email
from email import policy
from bs4 import BeautifulSoup
import os

eml_path = r"C:\Users\ARMANDO\Downloads\Tickets emitidos con éxito (2).eml"
with open(eml_path, 'rb') as f:
    msg = email.message_from_binary_file(f, policy=policy.default)

html_content = ""
for part in msg.walk():
    if part.get_content_type() == 'text/html':
        html_content = part.get_payload(decode=True).decode(part.get_content_charset() or 'utf-8', errors='ignore')
        break

if not html_content:
    text_content = ""
    for part in msg.walk():
        if part.get_content_type() == 'text/plain':
            text_content = part.get_payload(decode=True).decode(part.get_content_charset() or 'utf-8', errors='ignore')
            break
    print(f"No HTML found. Plain text length: {len(text_content)}")
    with open("estelar_debug.txt", "w", encoding="utf-8") as f:
        f.write(text_content)
else:
    print(f"HTML extracted. Length: {len(html_content)}")
    with open("estelar_debug.html", "w", encoding="utf-8") as f:
        f.write(html_content)

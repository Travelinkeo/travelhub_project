import email
from email import policy
import os

eml_path = r'C:\Users\ARMANDO\travelhub_project\media\boletos_importados\2026\02\E-TICKET_ITINERARY_RECEIPT_-_CASTANO_NINO_SEBASTIAN_CFTKi88.eml'

with open(eml_path, 'rb') as f:
    msg = email.message_from_binary_file(f, policy=policy.default)

plain_part = msg.get_body(preferencelist=('plain',))
html_part = msg.get_body(preferencelist=('html',))

plain_text = plain_part.get_content() if plain_part else ""
html_text = html_part.get_content() if html_part else ""

print("--- RAW PLAIN TEXT (FIRST 2000) ---")
print(plain_text[:2000])

print("\n--- RAW HTML TEXT (FIRST 2000) ---")
print(html_text[:2000])

# Also save to files for deeper look
with open('debug_1022_plain.txt', 'w', encoding='utf-8') as f:
    f.write(plain_text)
with open('debug_1022_html.html', 'w', encoding='utf-8') as f:
    f.write(html_text)


import os
import sys
import pdfplumber
import django
from django.conf import settings

# Setup Django
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from core.parsers.web_receipt_parser import WebReceiptParser
from core.ticket_parser import extract_data_from_text

# PDF PATH
pdf_path = r"C:\Users\ARMANDO\travelhub_project\media\boletos_importados\2026\01\Gmail_-_Fwd__Tickets_Avior_Airlines_FruhbRA.pdf"


with open("debug_output.txt", "w", encoding="utf-8") as f:
    f.write(f"--- DEBUGGING PDF: {pdf_path} ---\n")

    if not os.path.exists(pdf_path):
        f.write("ERROR: File not found!\n")
        sys.exit(1)

    # 1. EXTRACT TEXT
    text_content = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text_content += page.extract_text() + "\n"

    f.write("\n--- RAW TEXT CONTENT START ---\n")
    f.write(text_content)
    f.write("\n--- RAW TEXT CONTENT END ---\n")

    # 2. TEST WEBRECEIPT PARSER DIRECTLY
    f.write("\n--- TESTING WEBRECEIPT PARSER ---\n")
    parser = WebReceiptParser()
    try:
        result = parser.parse(text_content)
        f.write(f"WebReceiptParser Result: {result}\n")
    except Exception as e:
        f.write(f"WebReceiptParser Error: {e}\n")

    # 3. TEST FULL TICKET PARSER LOGIC
    f.write("\n--- TESTING FULL PIPELINE extract_data_from_text ---\n")
    try:
        full_result = extract_data_from_text(text_content)
        f.write(f"extract_data_from_text Result: {full_result}\n")
    except Exception as e:
        f.write(f"extract_data_from_text Error: {e}\n")



import pdfplumber
import os

def extract_from_pdf(path):
    print(f"\n--- FILE: {os.path.basename(path)} ---")
    try:
        with pdfplumber.open(path) as pdf:
            text = ""
            for page in pdf.pages:
                text += page.extract_text() + "\n"
            print(text[:2000]) # First 2000 chars
    except Exception as e:
        print(f"Error: {e}")

# Samples
samples = [
    r"C:\Users\ARMANDO\Downloads\Boletos\SABRE\Electronic ticket receipt, November 27 for BETLANA KELY MATA MONTANO.pdf",
    r"C:\Users\ARMANDO\Downloads\Boletos\COPA\Copa Airlines - Quovadis175 - 1.pdf"
]

for s in samples:
    extract_from_pdf(s)

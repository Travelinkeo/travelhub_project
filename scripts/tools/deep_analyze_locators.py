
import pdfplumber
import os
import re

def analyze_pdf(path):
    print(f"\n{'='*50}")
    print(f"ANALYZING: {os.path.basename(path)}")
    print(f"{'='*50}")
    try:
        with pdfplumber.open(path) as pdf:
            full_text = ""
            for i, page in enumerate(pdf.pages):
                text = page.extract_text() or ""
                full_text += text + "\n"
                print(f"--- PAGE {i+1} ---")
                print(text)
            
            print("\n--- LOCATOR ANALYSIS ---")
            # Look for PNR-like strings (6 chars)
            # Look for "Record Locator", "Airline", "Code"
            patterns = [
                r"Reservation Code[:\s]*([A-Z0-9]{6})",
                r"Booking Reference[:\s]*([A-Z0-9]{6})",
                r"Record Locator[:\s]*([A-Z0-9]{6})",
                r"Airline[:\s]*([A-Z0-9]{6})",
                r"Localizador[:\s]*([A-Z0-9]{6})"
            ]
            for p in patterns:
                matches = re.finditer(p, full_text, re.IGNORECASE)
                for m in matches:
                    print(f"FOUND MATCH: {m.group(0)}")
            
    except Exception as e:
        print(f"Error: {e}")

# Selection of samples from the folder provided by the user
samples = [
    r"C:\Users\ARMANDO\Downloads\Boletos\SABRE\Electronic ticket receipt, November 27 for BETLANA KELY MATA MONTANO.pdf",
    r"C:\Users\ARMANDO\Downloads\Boletos\COPA\Copa Airlines - Quovadis175 - 1.pdf",
    r"C:\Users\ARMANDO\Downloads\Boletos\KIU\Recibo de boleto electrónico, 19 enero para MR SEBASTIAN GOMEZ ZULUAGA.pdf"
]

for s in samples:
    if os.path.exists(s):
        analyze_pdf(s)
    else:
        print(f"File not found: {s}")

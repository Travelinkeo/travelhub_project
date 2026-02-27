
import pdfplumber
import re

def analyze_pdf(path, label):
    print(f"\n{'='*20} ANALYZING {label} {'='*20}")
    text = ""
    try:
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                text += page.extract_text() + "\n"
    except Exception as e:
        print(f"Error: {e}")
        return

    print(f"Total Length: {len(text)} chars")
    
    # Look for Price/Total
    print("--- PRICE / TOTAL SEARCH ---")
    price_keywords = ['Total', 'Fare', 'Tarifa', 'Monto', 'Amount', 'VES', 'USD', 'BS', 'Equiv']
    lines = text.split('\n')
    for i, line in enumerate(lines):
        if any(k.upper() in line.upper() for k in price_keywords):
            print(f"Line {i}: {line.strip()}")

    # Look for City/Airport details
    print("--- CITY DETAILS ---")
    city_keywords = ['BOGOTA', 'PARIS', 'SHANGHAI', 'COLOMBIA', 'FRANCE', 'CHINA']
    for i, line in enumerate(lines):
        if any(k in line.upper() for k in city_keywords):
            print(f"Line {i}: {line.strip()}")

analyze_pdf("original.pdf", "ORIGINAL SABRE PDF")
analyze_pdf("generated.pdf", "GENERATED TRAVELHUB PDF")

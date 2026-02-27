
import os
import sys
import django
import pdfplumber

try:
    import pypdf
except ImportError:
    pypdf = None

PDF_PATH = r"C:\Users\ARMANDO\Downloads\Recibo de pasaje electrónico, 22 diciembre para KEILIS PIZZANI DE SANTIAGO.pdf"

def main():
    text = ""
    # 1. PDFPlumber
    with pdfplumber.open(PDF_PATH) as pdf:
        for page in pdf.pages:
            text += (page.extract_text() or "") + "\n"
    
    # 2. PyPDF (Simulated)
    if pypdf:
        reader = pypdf.PdfReader(PDF_PATH)
        for page in reader.pages:
            text += (page.extract_text() or "") + "\n"
            
    # Search
    print("--- Searching for Headers/Markers ---")
    markers = ["Itinerario de Vuelo", "Por favor contacte a su agente", "AV 8396"]
    
    found_indices = {}
    lines = text.splitlines()
    for i, line in enumerate(lines):
        for m in markers:
            if m in line:
                print(f"MATCH (Line {i}): {line.strip()[:50]}...")
                found_indices[m] = i
    
    if "Itinerario de Vuelo" in found_indices and "Por favor contacte a su agente" in found_indices:
        start = found_indices["Itinerario de Vuelo"]
        end = found_indices["Por favor contacte a su agente"]
        if start < end:
            print("ORDER: Itinerary -> Footer (Standard)")
        else:
            print("ORDER: Footer -> Itinerary (Inverted!)")

if __name__ == "__main__":
    main()

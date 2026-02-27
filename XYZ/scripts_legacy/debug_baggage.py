
import pdfplumber
import re

PDF_PATH = r"C:\Users\ARMANDO\Downloads\Recibo de pasaje electrónico, 22 diciembre para KEILIS PIZZANI DE SANTIAGO.pdf"

def main():
    print(f"Analyzing Baggage in: {PDF_PATH}")
    text = ""
    print(f"Analyzing Baggage in: {PDF_PATH}")
    text = ""
    # Try pypdf first as it often gets hidden text better
    try:
        import pypdf
        print("--- Using PyPDF ---")
        reader = pypdf.PdfReader(PDF_PATH)
        for page in reader.pages:
            text += (page.extract_text() or "") + "\n"
    except ImportError:
        print("--- PyPDF not found, falling back to pdfplumber ---")
        with pdfplumber.open(PDF_PATH) as pdf:
            for page in pdf.pages:
                text += (page.extract_text() or "") + "\n"
    
    # Also dump raw text for manual inspection in output
    print("--- RAW TEXT DUMP (First 1000 chars) ---")
    print(text[:1000])
    
    print(f"--- Text Length: {len(text)} ---")
    
    # search for keywords
    keywords = ["PC", "KG", "Límite", "Baggage", "Equipaje", "Bag", "Franquicia"]
    
    found = False
    lines = text.splitlines()
    for i, line in enumerate(lines):
        for kw in keywords:
            if kw.upper() in line.upper():
                print(f"MATCH (Line {i}): {line.strip()}")
                found = True
                break
    
    if not found:
        print("No baggage keywords found in text layer!")

if __name__ == "__main__":
    main()

import os
import sys
import pdfplumber

def extract_text_from_pdf(file_path):
    text = ""
    try:
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text += (page.extract_text() or "") + "\n"
    except Exception as e:
        return f"Error: {e}"
    return text

file_path = r"c:\Users\ARMANDO\travelhub_project\core\tests\dataset\Gmail - E-TICKET ITINERARY RECEIPT - MURILLO CORTES_DIANA PATRICIA.pdf"
text = extract_text_from_pdf(file_path)

with open(r"c:\Users\ARMANDO\travelhub_project\core\tests\murillo_clean.txt", "w", encoding="utf-8") as f:
    f.write(text)

print("Done writing to murillo_clean.txt")

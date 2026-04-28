import pdfplumber
import sys

file_path = r"C:\Users\ARMANDO\Downloads\Boletos\SABRE\Recibo de pasaje electrónico, 19 marzo para ROSANGELA DIAZ SILVA.pdf"

try:
    with pdfplumber.open(file_path) as pdf:
        print(f"--- TEXT FROM {file_path} ---")
        for page in pdf.pages:
            text = page.extract_text()
            print(text)
            print("--- PAGE BREAK ---")
except Exception as e:
    print(f"Error: {e}")

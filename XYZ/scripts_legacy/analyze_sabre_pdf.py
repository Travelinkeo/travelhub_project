
import pdfplumber
import sys
import os

pdf_path = r"C:\Users\ARMANDO\Downloads\Boleto_2357338707424_20251008191917.pdf"

def analyze_pdf(path):
    print(f"Analyzing: {path}")
    if not os.path.exists(path):
        print("File not found!")
        return

    try:
        with pdfplumber.open(path) as pdf:
            full_text = ""
            for i, page in enumerate(pdf.pages):
                text = page.extract_text()
                print(f"--- Page {i+1} ---")
                print(text)
                full_text += text + "\n"
                
            print("\n--- End of PDF Text ---")
            
            with open("sabre_debug_output.txt", "w", encoding="utf-8") as f:
                f.write(full_text)
                
    except Exception as e:
        print(f"Error reading PDF with pdfplumber: {e}")

    try:
        from PyPDF2 import PdfReader
    except ImportError:
        try:
             from pypdf import PdfReader
        except ImportError:
            print("pypdf/PyPDF2 not installed")
            return

    print("\n--- Trying pypdf ---")
    try:
        reader = PdfReader(path)
        full_text_pypdf = ""
        for i, page in enumerate(reader.pages):
             text = page.extract_text()
             print(f"--- Page {i+1} (pypdf) ---")
             print(text)
             full_text_pypdf += text + "\n"
        
        with open("sabre_debug_output_pypdf.txt", "w", encoding="utf-8") as f:
            f.write(full_text_pypdf)
            
    except Exception as e:
        print(f"Error reading PDF with pypdf: {e}")

if __name__ == "__main__":
    analyze_pdf(pdf_path)


import sys
import os
from PyPDF2 import PdfReader

def analyze_pdf(path):
    print(f"Analyzing: {path}")
    try:
        reader = PdfReader(path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        
        with open('pdf_debug.txt', 'w', encoding='utf-8') as f:
            f.write(text)
        print("Text saved to pdf_debug.txt")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    analyze_pdf(r"c:\Users\ARMANDO\travelhub_project\core\tests\fixtures\venezuela_web\avior_sample.pdf")

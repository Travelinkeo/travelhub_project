import pdfplumber
import sys

# Raw input PDF from boletos_importados
pdf_path = r'c:\Users\ARMANDO\travelhub_project\media\boletos_importados\2025\11\Recibo_de_pasaje_electrónico_10_noviembre_para_ALEXANDER_CAST_CM8Z9Pz.pdf'

try:
    with pdfplumber.open(pdf_path) as pdf:
        text = ""
        for page in pdf.pages:
            text += page.extract_text() + "\n"
    print(text[:3000]) # Print first 3000 chars
except Exception as e:
    print(f"Error: {e}")

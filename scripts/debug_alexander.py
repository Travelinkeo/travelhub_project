
import pdfplumber
import sys
import os

pdf_path = r"c:\Users\ARMANDO\travelhub_project\media\boletos_importados\2026\01\Recibo_de_pasaje_electrónico_07_abril_para_ALEXANDER_CASTANO_VALENCIA.pdf"

if not os.path.exists(pdf_path):
    print(f"File not found: {pdf_path}")
    sys.exit(1)

text_content = ""
with pdfplumber.open(pdf_path) as pdf:
    for page in pdf.pages:
        text_content += page.extract_text() + "\n"

output_file = "alexander_text_utf8.txt"
with open(output_file, "w", encoding="utf-8") as f:
    f.write(text_content)

print(f"Text written to {output_file}")

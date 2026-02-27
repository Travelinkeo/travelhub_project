
import os
import sys
import django

sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from core.models import BoletoImportado
from core.ticket_parser import extract_data_from_text

# ID from screenshot URL (643)
BOLETO_ID = 643



from contextlib import redirect_stdout

with open("verification_log.txt", "w", encoding="utf-8") as f:
    with redirect_stdout(f):
        try:
            boleto = BoletoImportado.objects.get(pk=BOLETO_ID)
            print(f"Boleto Found: {boleto}")
            print(f"File Name: {boleto.archivo_boleto.name}")
            
            path = None
            try:
                path = boleto.archivo_boleto.path
                print(f"File Path: {path}")
                print(f"Path Exists: {os.path.exists(path)}")
            except Exception as e:
                print(f"Error accessing path: {e}")

            # Simulate Service Logic
            print("\n--- SIMULATING SERVICE ---")
            
            import pdfplumber
            text_input = ""
            if path and os.path.exists(path):
                with pdfplumber.open(path) as pdf:
                    for page in pdf.pages:
                        text_input += (page.extract_text() or "") + "\n"
            
            print("\n--- EXTRACTED TEXT START ---")
            print(text_input)
            print("--- EXTRACTED TEXT END ---\n")
            
            print("\nRunning extract_data_from_text(plain_text, pdf_path=path)...")
            result = extract_data_from_text(text_input, pdf_path=path)
            
            print("\n--- RESULT ---")
            print(result)
            print("\n")

        except Exception as e:
            print(f"Error: {e}")



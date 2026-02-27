import os
import django
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from core.models import BoletoImportado
import pdfplumber

def extract_text():
    try:
        b = BoletoImportado.objects.get(pk=424)
        print(f"Found Boleto 424: {b.archivo_boleto.name}")
        
        if b.archivo_boleto:
            temp_pdf = "temp_boleto_424.pdf"
            try:
                # Try path
                full_path = b.archivo_boleto.path
                print(f"Path from Django: {full_path}")
            except NotImplementedError:
                print("Remote storage. Downloading...")
                import requests
                url = b.archivo_boleto.url
                print(f"URL: {url}")
                if url.startswith('/'): # If local media url but no path support?
                     url = "http://127.0.0.1:8000" + url
                
                r = requests.get(url)
                if r.status_code == 200:
                    with open(temp_pdf, 'wb') as f:
                        f.write(r.content)
                    full_path = temp_pdf
                    print("✅ Downloaded to temp file.")
                else:
                    print(f"❌ Download failed: {r.status_code}")
                    return

        if os.path.exists(full_path):
            with pdfplumber.open(full_path) as pdf:
                text = pdf.pages[0].extract_text()
                with open("kiu_extraction.txt", "w", encoding="utf-8") as f:
                    f.write(text)
                print("✅ Text extracted to kiu_extraction.txt")
                
            # Cleanup
            if full_path == temp_pdf:
                os.remove(temp_pdf)
        else:
            print("❌ File not found")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    extract_text()

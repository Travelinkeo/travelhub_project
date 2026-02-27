
import os
import django
import sys

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "travelhub.settings")
django.setup()

from core.models.boletos import BoletoImportado
from django.conf import settings

def check_latest_pdf():
    print("--- CHECKING LAST BOLETO PDF ---")
    
    boleto = BoletoImportado.objects.order_by('-fecha_subida').first()
    
    if not boleto:
        print("No boletos found.")
        return

    print(f"Boleto ID: {boleto.pk}")
    print(f"Boleto Number: {boleto.numero_boleto}")
    print(f"Fecha: {boleto.fecha_subida}")
    
    if boleto.archivo_pdf_generado:
        print(f"PDF Field Name: {boleto.archivo_pdf_generado.name}")
        try:
            url = boleto.archivo_pdf_generado.url
            print(f"PDF URL: {url}")
            
            if "cloudinary" in url:
                print("HOST: Cloudinary ✅")
            else:
                print("HOST: Local filesystem ⚠️ (Likely causing WhatsApp failure)")
                
        except Exception as e:
            print(f"Error getting URL: {e}")
    else:
        print("No PDF generated for this boleto.")

    print(f"Cloudinary Enabled in Settings: {settings.USE_CLOUDINARY}")

if __name__ == "__main__":
    check_latest_pdf()

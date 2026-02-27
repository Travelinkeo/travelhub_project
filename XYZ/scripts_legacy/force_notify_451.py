
import os
import django
import sys

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "travelhub.settings")
django.setup()

from core.models.boletos import BoletoImportado
from core.services.notificaciones_boletos import notificar_boleto_procesado

def force_notify():
    print("--- FORCING NOTIFICATION FOR BOLETO 451 ---")
    
    try:
        boleto = BoletoImportado.objects.get(pk=451)
        print(f"Boleto: {boleto.numero_boleto}")
        print(f"PDF: {boleto.archivo_pdf_generado.url if boleto.archivo_pdf_generado else 'NONE'}")
        
        print("Promoting notification...")
        result = notificar_boleto_procesado(boleto)
        
        if result:
            print("Notification function returned TRUE ✅")
        else:
            print("Notification function returned FALSE ❌")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    force_notify()

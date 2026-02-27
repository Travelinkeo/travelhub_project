
import os
import django
import sys

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "travelhub.settings")
django.setup()

from core.models.boletos import BoletoImportado
from core.services.notificaciones_boletos import notificar_boleto_procesado

def force_notify():
    print("--- FORCING NOTIFICATION FOR LAST BOLETO ---")
    
    boleto = BoletoImportado.objects.order_by('-fecha_subida').first()
    
    if not boleto:
        print("No boletos found.")
        return

    print(f"Boleto: {boleto.numero_boleto} (ID: {boleto.pk})")
    print(f"PDF: {boleto.archivo_pdf_generado.url if boleto.archivo_pdf_generado else 'NONE'}")
    
    print("Promoting notification...")
    result = notificar_boleto_procesado(boleto)
    
    if result:
        print("Notification function returned TRUE ✅")
    else:
        print("Notification function returned FALSE ❌")

if __name__ == "__main__":
    force_notify()

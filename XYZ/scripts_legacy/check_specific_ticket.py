
import os
import django
import sys

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "travelhub.settings")
django.setup()

from core.models.boletos import BoletoImportado

def check_ticket():
    ticket_num = "308-0310903227" # Formatted with hyphen usually
    ticket_num_raw = "3080310903227"
    
    print(f"--- CHECKING TICKET {ticket_num}/{ticket_num_raw} ---")
    
    boletos = BoletoImportado.objects.filter(numero_boleto__icontains=ticket_num) | BoletoImportado.objects.filter(numero_boleto__icontains=ticket_num_raw)
    
    if boletos.exists():
        for b in boletos:
            print(f"FOUND: ID {b.pk} | Num: {b.numero_boleto}")
            print(f"   PDF: {b.archivo_pdf_generado.url if b.archivo_pdf_generado else 'NONE'}")
            print(f"   Venta: {b.venta_asociada}")
            print(f"   Agencia: {b.agencia}")
            print(f"   Fecha: {b.fecha_subida}")
    else:
        print("❌ NOT FOUND in Database.")

if __name__ == "__main__":
    check_ticket()

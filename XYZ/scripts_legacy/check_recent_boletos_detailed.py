
import os
import django
import sys
from django.utils import timezone

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "travelhub.settings")
django.setup()

from core.models.boletos import BoletoImportado

def check_recent_boletos():
    print("--- CHECKING RECENT BOLETOS ---")
    boletos = BoletoImportado.objects.order_by('-fecha_subida')[:3]
    
    for b in boletos:
        print(f"ID: {b.pk} | Num: {b.numero_boleto} | Fecha: {b.fecha_subida}")
        print(f"   PDF: {b.archivo_pdf_generado.name if b.archivo_pdf_generado else 'NONE'}")
        
        # Check Venta
        if b.venta_asociada:
            print(f"   Venta: {b.venta_asociada.pk} | Cliente: {b.venta_asociada.cliente}")
        else:
            print(f"   Venta: NONE")
            
        # Check Parsed Data specific keys
        data = b.datos_parseados or {}
        pnr = data.get('SOLO_CODIGO_RESERVA') or data.get('pnr') or 'N/A'
        print(f"   PNR Parsed: {pnr}")
        print("-" * 30)

if __name__ == "__main__":
    check_recent_boletos()

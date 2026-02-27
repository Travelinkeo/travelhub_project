
import os
import django
import sys

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "travelhub.settings")
django.setup()

from core.models.boletos import BoletoImportado

def check_venta():
    print("--- CHECKING BOLETO 449 VENTA ---")
    
    try:
        boleto = BoletoImportado.objects.get(pk=449)
        print(f"Boleto: {boleto.numero_boleto}")
        
        if boleto.venta_asociada:
            print(f"Venta Asociada: {boleto.venta_asociada} (ID: {boleto.venta_asociada.pk})")
        else:
            print("❌ NO VENTA ASOCIADA")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_venta()

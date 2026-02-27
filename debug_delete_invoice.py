
import os
import django
from django.conf import settings

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from apps.finance.models import Factura
from core.models import Venta

def fix_invoice(pk):
    try:
        f = Factura.objects.get(pk=pk)
        print(f"Eliminando factura corrupta {pk}...")
        f.delete()
        print("Eliminada.")
        
        # Verify Venta
        v = Venta.objects.get(pk=157)
        print(f"Venta {v.pk} Factura es ahora: {v.factura}")
        
    except Factura.DoesNotExist:
        print(f"Factura {pk} no existe.")

if __name__ == "__main__":
    fix_invoice(6)

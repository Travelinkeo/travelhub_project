
import os
import django
from django.conf import settings

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from core.models import Venta

def check_sale():
    try:
        v = Venta.objects.get(pk=157)
        print(f"Venta {v.pk} Factura: {v.factura}")
        if v.factura:
            print(f"Factura ID: {v.factura.pk}")
            print(f"Numero: {v.factura.numero_factura}")
            print(f"Total: {v.factura.monto_total}")
            print(f"Items: {v.factura.items_factura.count()}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_sale()

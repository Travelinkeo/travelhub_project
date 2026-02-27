
import os
import django
from django.conf import settings

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from apps.finance.models import Factura

def inspect_invoice(pk):
    try:
        f = Factura.objects.get(pk=pk)
        print(f"--- Factura PK={pk} ---")
        print(f"Numero: '{f.numero_factura}'")
        print(f"Estado: {f.estado}")
        print(f"Cliente: {f.cliente}")
        print(f"Venta: {f.venta_asociada}")
        print(f"Fecha: {f.fecha_emision}")
        print(f"Monto Total: {f.monto_total}")
        print(f"Items: {f.items_factura.count()}")
    except Factura.DoesNotExist:
        print(f"Factura {pk} no existe.")

if __name__ == "__main__":
    inspect_invoice(5)

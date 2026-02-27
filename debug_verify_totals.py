
import os
import django
from django.conf import settings

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from apps.finance.models import Factura

def check_invoice(pk):
    try:
        f = Factura.objects.get(pk=pk)
        print(f"--- Factura {f.numero_factura} (PK={pk}) ---")
        print(f"Subtotal: {f.subtotal}")
        print(f"Base Imponible: {f.base_imponible}")
        print(f"Base Exenta: {f.base_exenta}")
        print(f"IVA ({f.iva_porcentaje}%): {f.iva_monto}")
        print(f"IGTF ({f.igtf_porcentaje}%): {f.igtf_monto}")
        print(f"INATUR ({f.inatur_porcentaje}%): {f.inatur_monto}")
        print(f"Monto Impuestos: {f.monto_impuestos}")
        print(f"Monto Total: {f.monto_total}")
        print(f"Items: {f.items_factura.count()}")
        for item in f.items_factura.all():
            print(f"  - {item.descripcion}: {item.cantidad} x {item.precio_unitario} = {item.subtotal_item} (Impuesto: {item.get_tipo_impuesto_display()})")
    except Factura.DoesNotExist:
        print(f"Factura {pk} no existe.")

if __name__ == "__main__":
    check_invoice(16)

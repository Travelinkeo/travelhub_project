import os
import sys
import django

sys.path.append(os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "travelhub.settings")
django.setup()

from apps.bookings.models import BoletoImportado

def list_latest():
    # Only select PK and Status to avoid triggering complex __str__ or related lookups
    boletos = BoletoImportado.objects.all().order_by('-fecha_subida').values('pk', 'estado_parseo', 'fecha_subida')[:5]
    for b in boletos:
        print(f"ID: {b['pk']}, Status: {b['estado_parseo']}, Date: {b['fecha_subida']}")

if __name__ == "__main__":
    list_latest()


import os
import django
import sys

sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from apps.bookings.models import BoletoImportado

b = BoletoImportado.objects.order_by('-pk').first()
if b:
    print(f"ID: {b.pk}")
    print(f"Estado Parseo: {b.estado_parseo}")
    print(f"Log: {b.log_parseo}")
    print(f"Datos Parseados Keys: {list(b.datos_parseados.keys()) if b.datos_parseados else 'None'}")
else:
    print("No boletos found.")

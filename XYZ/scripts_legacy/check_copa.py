import os
import django
import sys

sys.path.append(r"C:\Users\ARMANDO\travelhub_project")
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from core.models import BoletoImportado

print("--- COPA CHECK (KW23RU) ---")
copas = BoletoImportado.objects.filter(datos_parseados__icontains='KW23RU').order_by('-fecha_subida')
for c in copas:
    print(f"ID: {c.pk} | Ticket: {c.numero_boleto} | Date: {c.fecha_subida}")

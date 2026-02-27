import os
import django
import sys
import json

sys.path.append(r"C:\Users\ARMANDO\travelhub_project")
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from core.models import BoletoImportado

print("--- COPA CHECK (KW23RU) ---")
copa = BoletoImportado.objects.filter(datos_parseados__icontains='KW23RU').first()
if copa:
    print(f"Found Copa! ID: {copa.pk} | Ticket: {copa.numero_boleto} | GDS: {copa.datos_parseados.get('gds_detected', 'N/A')}")
else:
    print("Copa KW23RU NOT FOUND in datos_parseados.")

print("\n--- PENDIENTE CHECK ---")
pendientes = BoletoImportado.objects.filter(numero_boleto='PENDIENTE').order_by('-fecha_subida')[:3]
for p in pendientes:
    print(f"ID: {p.pk} | Date: {p.fecha_subida}")
    print(f"Parseo snippet: {str(p.datos_parseados)[:500]}")

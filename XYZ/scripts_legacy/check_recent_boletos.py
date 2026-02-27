import os
import django
import sys

# Setup Django
sys.path.append(r"C:\Users\ARMANDO\travelhub_project")
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from core.models import BoletoImportado

print(f"Total Boletos: {BoletoImportado.objects.count()}")
for b in BoletoImportado.objects.order_by('-fecha_subida')[:5]:
    print(f"ID: {b.pk} | PNR: {b.localizador_pnr} | Boleto: {b.numero_boleto} | GDS: {b.datos_parseados.get('gds_detected', 'N/A')} | Fecha: {b.fecha_subida}")

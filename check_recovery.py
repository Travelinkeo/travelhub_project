
import os
import django
from django.conf import settings

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from apps.bookings.models import BoletoImportado

def check():
    total = BoletoImportado.objects.count()
    parsed = BoletoImportado.objects.filter(estado_parseo='COM').count()
    pending = BoletoImportado.objects.filter(estado_parseo='PEN').count()
    errors = BoletoImportado.objects.filter(estado_parseo='ERR').count()
    
    conviasa_v0 = BoletoImportado.objects.filter(aerolinea_emisora__icontains='V0').count()
    conviasa_txt = BoletoImportado.objects.filter(aerolinea_emisora__icontains='Conviasa').count()
    
    print(f"Total Boletos: {total}")
    print(f"Parsed (COM): {parsed}")
    print(f"Pending (PEN): {pending}")
    print(f"Errors (ERR): {errors}")
    print(f"Conviasa (V0): {conviasa_v0}")
    print(f"Conviasa (Text): {conviasa_txt}")
    
    if conviasa_v0 > 0 or conviasa_txt > 0:
        print("\nConviasa Tickets Found:")
        qs = BoletoImportado.objects.filter(aerolinea_emisora__icontains='V0') | BoletoImportado.objects.filter(aerolinea_emisora__icontains='Conviasa')
        for b in qs[:5]:
            print(f"- ID {b.pk}: {b.aerolinea_emisora} / PNR: {b.localizador_pnr} / File: {b.archivo_boleto.name}")

if __name__ == '__main__':
    check()

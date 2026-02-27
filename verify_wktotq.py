
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from apps.bookings.models import BoletoImportado
from django.db.models import Q

def verify():
    print("Verifying PNR WKTOTQ...")
    qs = BoletoImportado.objects.filter(
        Q(localizador_pnr__icontains='WKTOTQ') | 
        Q(log_parseo__icontains='WKTOTQ')
    )
    
    count = qs.count()
    print(f"Total Found: {count}")
    
    for b in qs:
        print(f"ID: {b.pk} | PNR: {b.localizador_pnr} | Name: '{b.nombre_pasajero_completo}' | File: {b.archivo_boleto.name}")

if __name__ == '__main__':
    verify()

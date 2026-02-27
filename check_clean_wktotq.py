
import os
import django
import sys

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "true")
django.setup()

from apps.bookings.models import BoletoImportado
from django.db.models import Q

def check_and_clean():
    print("Checking DB for WKTOTQ...")
    qs = BoletoImportado.objects.filter(
        Q(localizador_pnr__icontains='WKTOTQ') | 
        Q(log_parseo__icontains='WKTOTQ')
    )
    
    count = qs.count()
    print(f"Found {count} records.")
    
    if count > 0:
        print("Records found:")
        for b in qs:
            print(f"ID: {b.pk} | PNR: {b.localizador_pnr} | Name: {b.nombre_pasajero_completo}")
        
        # Uncomment to delete if needed, but for now just list
        # print("Deleting records to allow fresh re-processing...")
        # qs.delete()
        # print("Deleted.")
    else:
        print("No records found. Clean slate.")

if __name__ == '__main__':
    check_and_clean()

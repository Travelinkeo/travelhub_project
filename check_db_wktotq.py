
import os
import django
import logging

# Setup Django exactly like fetch_missing_emails.py which worked
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "true")
django.setup()

from apps.bookings.models import BoletoImportado
from django.db.models import Q

def check():
    print("Checking DB for WKTOTQ...")
    qs = BoletoImportado.objects.filter(
        Q(localizador_pnr__icontains='WKTOTQ') | 
        Q(log_parseo__icontains='WKTOTQ')
    ).order_by('-fecha_subida')
    
    count = qs.count()
    print(f"Total Found: {count}")
    
    for b in qs:
        print(f"ID: {b.pk}")
        print(f"PNR: {b.localizador_pnr}")
        print(f"Name: {b.nombre_pasajero_completo}") # Check if full name!
        print(f"File: {b.archivo_boleto.name}")
        print("-" * 20)

if __name__ == '__main__':
    check()

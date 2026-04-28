
import os
import sys
import django

sys.path.append(os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "travelhub.settings")
django.setup()

from core.models import Agencia
from apps.bookings.models import BoletoImportado

def fix_orphans():
    print("-" * 50)
    print("FIXING ORPHAN BOLETOS")
    print("-" * 50)
    
    try:
        travelinkeo = Agencia.objects.get(pk=1) # ID 1 is Travelinkeo
        orphans = BoletoImportado.objects.filter(agencia__isnull=True)
        count = orphans.count()
        
        if count > 0:
            print(f"Found {count} orphan boletos. Assigning to {travelinkeo.nombre}...")
            orphans.update(agencia=travelinkeo)
            print("Done.")
        else:
            print("No orphans found.")
            
    except Agencia.DoesNotExist:
        print("Agencia Travelinkeo (ID 1) not found!")

if __name__ == "__main__":
    fix_orphans()

import os
import sys
import django
from django.db.models import Count

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "travelhub.settings")
django.setup()

from core.models import HotelTarifario

def remove_duplicates():
    duplicates = HotelTarifario.objects.values('nombre').annotate(count=Count('id')).filter(count__gt=1)
    
    print(f"Found {duplicates.count()} duplicated names.")
    
    for dep in duplicates:
        nombre = dep['nombre']
        hoteles = HotelTarifario.objects.filter(nombre=nombre).order_by('-id') # Keep the newest (highest ID)
        
        # Ensure we have at least 1 to keep
        if hoteles.count() > 1:
            keep = hoteles[0]
            remove = hoteles[1:]
            
            print(f"Keeping {keep.nombre} (ID: {keep.id}). Removing {len(remove)} duplicates.")
            for h in remove:
                print(f" - Deleting ID {h.id}")
                h.delete()
        else:
             print(f"Skipping {nombre}, not enough duplicates found.")

if __name__ == "__main__":
    remove_duplicates()

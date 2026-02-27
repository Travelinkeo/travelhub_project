
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from core.models.cotizaciones import Cotizacion as CoreCot
from core.models.cotizaciones import ItemCotizacion as CoreItem
from cotizaciones.models import Cotizacion as LocalCot
from cotizaciones.models import ItemCotizacion as LocalItem

def check_cotizacion(pk):
    print(f"--- Checking Cotizacion ID {pk} ---")
    
    # Check Core
    try:
        core_obj = CoreCot.objects.get(pk=pk)
        core_items_count = core_obj.items_cotizacion.count()
        print(f"CORE: Found. Items count: {core_items_count} (via items_cotizacion)")
        # Also check backwards compat related_name if any
        try:
           print(f"CORE (set): {core_obj.itemcotizacion_set.count()}")
        except:
           pass
    except CoreCot.DoesNotExist:
        print(f"CORE: Not Found")

    # Check Local
    try:
        local_obj = LocalCot.objects.get(pk=pk)
        # Local model uses default related_name 'items' (from my view of models.py line 103)
        local_items_count = local_obj.items.count()
        print(f"LOCAL: Found. Items count: {local_items_count}")
    except LocalCot.DoesNotExist:
        print(f"LOCAL: Not Found")

if __name__ == '__main__':
    check_cotizacion(35)

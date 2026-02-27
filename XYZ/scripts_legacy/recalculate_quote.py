
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from core.models.cotizaciones import Cotizacion

def recalculate(pk):
    try:
        cot = Cotizacion.objects.get(pk=pk)
        print(f"Before: Total={cot.total_cotizado}, Subtotal={cot.subtotal}")
        cot.calcular_total()
        # Refresh from db to be sure
        cot.refresh_from_db()
        print(f"After: Total={cot.total_cotizado}, Subtotal={cot.subtotal}")
    except Cotizacion.DoesNotExist:
        print(f"Cotizacion {pk} not found")

if __name__ == '__main__':
    recalculate(35)

import os
import django
from django.db.models import Count

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from apps.bookings.models import Venta

try:
    # Intenta realizar la consulta que fallaba en el dashboard
    ventas_recientes = Venta.objects.select_related('cliente').order_by('-fecha_venta')[:5]
    count = len(ventas_recientes)
    print(f"Consulta exitosa! Se encontraron {count} ventas recientes.")
    for v in ventas_recientes:
        cliente_nombres = v.cliente.nombres if v.cliente else "N/A"
        print(f"Venta: {v.localizador} - Cliente: {cliente_nombres}")
except Exception as e:
    print(f"Error al realizar la consulta: {e}")

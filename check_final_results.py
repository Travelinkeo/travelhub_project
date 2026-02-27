
import os
import django
import sys

sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from apps.bookings.models import BoletoImportado

qs = BoletoImportado.objects.order_by('-pk')[:5]
for b in qs:
    name = b.nombre_pasajero_completo
    flights = b.datos_parseados.get('flights', []) if b.datos_parseados else []
    print(f"ID: {b.pk} | FMT: {b.formato_detectado} | EST: {b.estado_parseo}")
    print(f"  Name: {name}")
    print(f"  Segments: {len(flights)}")
    if flights:
        print(f"  First Flight: {flights[0].get('numero_vuelo')} {flights[0].get('origen')}->{flights[0].get('destino')}")
    print(f"  Log: {str(b.log_parseo)[:100]}")
    print("-" * 20)

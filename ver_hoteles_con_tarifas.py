import django
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from core.models import HotelTarifario

hoteles = HotelTarifario.objects.all()
for h in hoteles:
    tarifas = sum(t.tarifas.count() for t in h.tipos_habitacion.all())
    if tarifas > 0:
        print(f'{h.nombre}: {tarifas} tarifas')

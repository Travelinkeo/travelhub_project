import django
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from core.models import HotelTarifario

destinos = {}
for hotel in HotelTarifario.objects.all():
    destino = hotel.destino
    if destino not in destinos:
        destinos[destino] = 0
    destinos[destino] += 1

print("Hoteles por destino:")
for destino, count in sorted(destinos.items()):
    print(f"{destino}: {count}")

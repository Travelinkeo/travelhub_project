import django
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from core.models import HotelTarifario

hoteles = HotelTarifario.objects.filter(nombre__icontains='ISLA LINDA')
for hotel in hoteles:
    print(f"\nHotel: {hotel.nombre}")
    print(f"Destino: {hotel.destino}")
    print(f"Régimen: {hotel.get_regimen_display()}")
    for tipo_hab in hotel.tipos_habitacion.all():
        print(f"  Tipo: {tipo_hab.nombre}")
        for tarifa in tipo_hab.tarifas.all():
            print(f"    {tarifa.fecha_inicio} - {tarifa.fecha_fin}: {tarifa.moneda} {tarifa.tarifa_dbl}")

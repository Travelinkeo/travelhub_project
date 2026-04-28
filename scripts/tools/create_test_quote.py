import os
import django
import uuid
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from apps.cotizaciones.models import Cotizacion
from core.models import Moneda
from django.contrib.auth.models import User

# Asegurar que existe USD
usd, _ = Moneda.objects.get_or_create(codigo_iso='USD', defaults={'nombre': 'Dólar Estadounidense', 'simbolo': '$'})

user = User.objects.first()
c = Cotizacion.objects.create(
    destino='Madrid, España',
    nombre_cliente_manual='Familia González',
    consultor=user,
    moneda=usd,
    total_cotizado=770.00,
    agency_fee=50.00,
    image_url='https://images.unsplash.com/photo-1542314831-068cd1dbfeeb?q=80&w=800',
    metadata_ia={
        'destination': 'Madrid',
        'type': 'Escapada Europea',
        'outboundDate': '15 Oct',
        'returnDate': '30 Oct',
        'flights': [
            {
                'airline': 'Air Europa',
                'departureCode': 'CCS',
                'arrivalCode': 'MAD',
                'departureTime': '12:10',
                'arrivalTime': '06:15',
                'stops': 'Directo',
                'baggage': '1 Maleta 23kg'
            },
            {
                'airline': 'Air Europa',
                'departureCode': 'MAD',
                'arrivalCode': 'CCS',
                'departureTime': '15:00',
                'arrivalTime': '18:20',
                'stops': 'Directo',
                'baggage': '1 Maleta 23kg'
            }
        ]
    }
)
print(f'http://127.0.0.1:8000/api/public/{c.uuid}/')

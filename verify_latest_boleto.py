
import os
import django
import sys

sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from apps.bookings.models import BoletoImportado

b = BoletoImportado.objects.order_by('-pk').first()
if b:
    print(f"ID: {b.pk}")
    print(f"Format: {b.formato_detectado}")
    print(f"Passenger: {b.datos_parseados.get('passenger_name')}")
    flights = b.datos_parseados.get('flights', [])
    print(f"Itinerary Segments: {len(flights)}")
    if flights:
        print(f"First Flight: {flights[0]}")
    print(f"PDF: {b.archivo_pdf_generado}")
else:
    print("No boletos found.")

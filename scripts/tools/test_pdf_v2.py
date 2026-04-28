import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from core.services.parsers.pdf_generation import PdfGenerationService
from core.models import Agencia

data = {
    'SOURCE_SYSTEM': 'KIU',
    'NOMBRE_DEL_PASAJERO': 'DIAZ SILVA/ROSANGELA',
    'CODIGO_IDENTIFICACION': 'V13835630',
    'NUMERO_DE_BOLETO': '7402400321456',
    'FECHA_DE_EMISION': '08 MAY 25',
    'SOLO_CODIGO_RESERVA': 'WPYVSD',
    'vuelos': [
        {
            'numero_vuelo': 'AV 46',
            'fecha_salida': '22 MAY 25',
            'origen': 'BOG',
            'destino': 'MAD',
            'hora_salida': '07:00'
        }
    ]
}

agencia = Agencia.objects.first()
print(f"Testing PDF generation for {agencia.nombre}...")
pdf_bytes, filename = PdfGenerationService.generate_ticket(data, agencia_obj=agencia)

if pdf_bytes:
    with open("test_ticket_generated.pdf", "wb") as f:
        f.write(pdf_bytes)
    print(f"SUCCESS: {filename}")
else:
    print(f"FAILURE: {filename}")

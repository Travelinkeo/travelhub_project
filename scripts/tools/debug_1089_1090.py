
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from apps.bookings.models import BoletoImportado
from core.services.ticket_parser_service import TicketParserService
from core.ticket_parser import extract_data_from_text

service = TicketParserService()

for bid in [1090]:
    try:
        b = BoletoImportado.objects.get(pk=bid)
        print(f"\n--- TICKET {bid} ({b.archivo_boleto.name}) ---")
        text = service._extraer_texto(b)
        print("TEXTO EXTRAIDO (Primeros 2000 caracteres):")
        print(text[:2000])
        print("-" * 50)
        
        # Probar detección y parseo
        data = extract_data_from_text(text)
        print("SISTEMA DETECTADO:", data.get('SOURCE_SYSTEM'))
        print("PASAJERO:", data.get('NOMBRE_DEL_PASAJERO') or data.get('NOMBRE DEL PASAJERO'))
        print("DOCUMENTO:", data.get('CODIGO_IDENTIFICACION') or data.get('CODIGO IDENTIFICACION'))
        print("AGENTE (IATA):", data.get('AGENTE_EMISOR') or data.get('AGENTE EMISOR'))
        
    except Exception as e:
        print(f"Error con ticket {bid}: {e}")

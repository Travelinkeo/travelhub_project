
import os
import sys
import django

sys.path.append(os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "travelhub.settings")
django.setup()

from apps.bookings.models import BoletoImportado
from core.services.ticket_parser_service import TicketParserService

try:
    boleto_id = int(sys.argv[1]) if len(sys.argv) > 1 else 959
    print(f"Buscando Boleto ID {boleto_id}...")
    boleto = BoletoImportado.objects.get(pk=boleto_id)
    print(f"Estado actual: {boleto.estado_parseo}")
    
    print("Iniciando procesamiento manual...")
    service = TicketParserService()
    resultado = service.procesar_boleto(boleto_id)
    print(f"Resultado: {resultado}")
    
except BoletoImportado.DoesNotExist:
    print(f"Boleto {boleto_id} no encontrado.")
except Exception as e:
    print(f"Error procesando boleto: {e}")
    import traceback
    traceback.print_exc()

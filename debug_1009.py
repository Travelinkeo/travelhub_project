import os
import django
import traceback

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from core.models import BoletoImportado
from core.services.ticket_parser_service import TicketParserService

def debug_1009():
    try:
        b = BoletoImportado.objects.get(pk=1009)
        b.estado_parseo = 'PEN'
        b.localizador_pnr = None
        b.save()
        
        service = TicketParserService()
        print("--- Iniciando procesar_boleto(1009) ---")
        service.procesar_boleto(1009)
        print("--- Finalizado (sin excepción capturada por try/except exterior) ---")
    except Exception:
        print("--- TRACEBACK DETECTADO ---")
        traceback.print_exc()

if __name__ == "__main__":
    debug_1009()

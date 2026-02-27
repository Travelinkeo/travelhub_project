import os
import django
import sys

sys.path.append('c:\\Users\\ARMANDO\\travelhub_project')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "travelhub.settings")
django.setup()

from core.models import BoletoImportado
from core.services.ticket_parser_service import TicketParserService
import logging

# Configure logger to print to stdout
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def debug():
    try:
        boleto = BoletoImportado.objects.get(pk=980)
        print(f"Boleto ID: {boleto.pk}", flush=True)
        print("Testing patched TicketParserService...", flush=True)
        service = TicketParserService()
        print("Extracting text...", flush=True)
        text = service._extraer_texto(boleto)
        print(f"Extracted text length: {len(text) if text else 'None'}", flush=True)
        if text:
            print("Preview:", flush=True)
            print(text[:500], flush=True)
            
            # Find the actual label for Reservation Code
            print("\nSearching for RESERVA/CODIGO labels:", flush=True)
            for line in text.split('\n'):
                if 'RESERVA' in line.upper() or 'CODIGO' in line.upper() or 'CODE' in line.upper():
                    print(f"MATCH: {line.strip()}", flush=True)
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug()

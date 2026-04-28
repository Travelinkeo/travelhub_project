import os
import django
import sys

sys.path.append('c:\\Users\\ARMANDO\\travelhub_project')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "travelhub.settings")
django.setup()

from apps.bookings.models import BoletoImportado
from core.services.ticket_parser_service import TicketParserService
from core.parsers.sabre_parser import SabreParser
import logging

logging.basicConfig(level=logging.INFO)

def debug_flights():
    try:
        boleto = BoletoImportado.objects.get(pk=980)
        print(f"Loading Boleto ID: {boleto.pk}")
        
        service = TicketParserService()
        text = service._extraer_texto(boleto)
        
        if not text:
            print("Error: No text extracted")
            return

        print("--- Text Preview (Lines 11-40) ---", flush=True)
        lines = text.split('\n')
        for i in range(11, min(40, len(lines))):
             print(f"{i}: [{lines[i].strip()}]", flush=True)
        print("-------------------------------", flush=True)

        parser = SabreParser()
        print("\n--- Running _parse_flights ---")
        flights = parser._parse_flights(text)
        print(f"Flights found: {len(flights)}")
        for i, f in enumerate(flights):
            print(f"Flight {i+1}: {f}")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_flights()

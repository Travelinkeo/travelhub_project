
import os
import sys
import django

sys.path.append(os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "travelhub.settings")

print(f"DEBUG: CWD: {os.getcwd()}")
try:
    import apps.bookings
    print(f"DEBUG: Pre-setup import apps.bookings: OK")
except Exception as e:
    print(f"DEBUG: Pre-setup import apps.bookings: FAILED ({e})")

django.setup()

print("Django setup done.")

try:
    print("Importing Cliente from apps.crm.models...")
    from apps.crm.models import Cliente
    print("OK.")
except Exception as e:
    print(f"Error importing Cliente: {e}")

try:
    print("Importing Venta from core.models (which maps to apps.bookings)...")
    from apps.bookings.models import Venta
    print("OK.")
except Exception as e:
    print(f"Error importing Venta: {e}")

try:
    print("Importing TicketParserService...")
    from core.services.ticket_parser_service import TicketParserService
    print("OK.")
except Exception as e:
    print(f"Error importing TicketParserService: {e}")

print("All imports valid.")

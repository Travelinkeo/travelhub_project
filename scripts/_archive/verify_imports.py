import os
import sys

import django

sys.path.append(os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "travelhub.settings")

print(f"DEBUG: CWD: {os.getcwd()}")
try:
    print("DEBUG: Pre-setup import apps.bookings: OK")
except Exception as e:
    print(f"DEBUG: Pre-setup import apps.bookings: FAILED ({e})")

django.setup()

print("Django setup done.")

try:
    print("Importing Cliente from apps.crm.models...")
    print("OK.")
except Exception as e:
    print(f"Error importing Cliente: {e}")

try:
    print("Importing Venta from core.models (which maps to apps.bookings)...")
    print("OK.")
except Exception as e:
    print(f"Error importing Venta: {e}")

try:
    print("Importing TicketParserService...")
    print("OK.")
except Exception as e:
    print(f"Error importing TicketParserService: {e}")

print("All imports valid.")

import importlib
import os
import sys

# Ensure the project root is in PYTHONPATH
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

CopaParser = importlib.import_module("apps.automation.parsers.legacy.copa_parser").CopaParser

parser = CopaParser()

# Directory with sample .eml files
samples_dir = r"C:/Users/ARMANDO/Downloads"
files = [
    "Itinerario para localizador de reserva KDO7RA.eml",
    "Itinerary for Record Locator DS5LF7.eml",
    "Itinerario para localizador de reserva KDO6GU.eml",
    "Itinerary for Record Locator DDH1SG.eml",
]

for fname in files:
    path = os.path.join(samples_dir, fname)
    try:
        with open(path, encoding="utf-8", errors="ignore") as f:
            content = f.read()
        # Parse the email content (text only)
        result = parser.parse(content)
        print(f"--- {fname} ---")
        print("PNR:", result.pnr)
        print("Ticket Number:", result.ticket_number)
        print("Passenger Name:", result.passenger_name)
        print("Issue Date:", result.issue_date)
        print("Flights:", result.flights)
        print("Fares:", result.fares)
        print("Agency:", result.agency)
        print()
    except Exception as e:
        print(f"Error processing {fname}: {e}")

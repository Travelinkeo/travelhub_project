import sys
import os
import django

# Setup Django
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from core.parsers.kiu_parser import KIUParser

sample_text = """
KIUSYS.COM                       ITINERARY RECEIPT                      05 FEB 2026
                                 RECIBO DE ITINERARIO
 
Issue Agent/Agente Emisor:       AGENCIA DE VIAJES TRAVELHUB
                                 BLA12345
Name/Nombre:                     PEREZ/JUAN MR
Ticket Number/Boleto Nro:        308-0201387528
Booking Ref./Localizador:        C1/ABC123

FROM/TO             FLIGHT  CL DATE   DEP  ARR  BAG  ST
DESDE/HACIA         VUELO   CL FECHA  SALE LLEG EQ   EST
CARACAS             V03750  Q  14FEB  0700 0745 1PC  OK
MAIQUETIA
PORLAMAR
SANTIAGO MARINO

PORLAMAR            V03751  Q  18FEB  1800 1845 1PC  OK
SANTIAGO MARINO
CARACAS
MAIQUETIA

Form of Payment/Forma de Pago:   CASH
Total:                           VES 5.500,00
"""

def test_extraction():
    parser = KIUParser()
    parsed_data = parser.parse(sample_text)
    
    print("--- TESTING FLIGHT EXTRACTION ---")
    print(f"Passenger: {parsed_data.passenger_name}")
    print(f"PNR: {parsed_data.pnr}")
    print(f"Flights Found: {len(parsed_data.flights)}")
    
    for f in parsed_data.flights:
        print(f"- {f['aerolinea']} {f['numero_vuelo']} {f['origen']}->{f['destino']}")

    if not parsed_data.flights:
        print("\n[FAIL] No flights extracted!")
        sys.exit(1)
    else:
        print("\n[SUCCESS] Flights extracted.")

if __name__ == '__main__':
    test_extraction()

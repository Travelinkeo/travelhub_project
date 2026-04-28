import os
import sys
import django
from decimal import Decimal

# Setup Django Environment
sys.path.append('c:/Users/ARMANDO/travelhub_project')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from apps.automation.services.ai_router import GeminiRouter, EmailType

def test_ai_router():
    print("--- 🧪 Testing AI Router ---")
    
    try:
        router = GeminiRouter()
        print("✅ Router Initialization: Success")
    except Exception as e:
        print(f"❌ Router Initialization Failed: {e}")
        return

    # Sample 1: A clear Sabre ticket string
    sabre_text = """
    ISSUING AIRLINE     : AMERICAN AIRLINES
    TICKET NUMBER       : 001 2345678901
    BOOKING REF : ABCDEF
    FROM /TO             FLIGHT  CL DATE   DEP      FARE BASIS   NVB   NVA   BAG  ST
    MADRID BARAJAS       AA 37   Q  20FEB  1100     QLE7M2Z      20FEB 20FEB 1PC  OK
    DALLAS FT WORTH      AA 38   Q  28FEB  1800     QLE7M2Z      28FEB 28FEB 1PC  OK
    
    FARE CALC : MAD AA DFW 200.00NUC200.00END ROE1.00
    AIR FARE  : USD 400.00
    TAX       : USD 50.00 YQ
    TOTAL     : USD 450.00
    PASSENGER : DOE/JOHN MR
    """
    
    print("\n--- Test Case 1: Sabre Ticket ---")
    category = router.classify_email(sabre_text)
    print(f"Category: {category}")
    
    if category in [EmailType.TICKET_ISSUANCE, EmailType.SCHEDULE_CHANGE]:
        print("Extracting Data...")
        ticket = router.extract_ticket_data(sabre_text)
        if ticket:
            print(f"PNR: {ticket.pnr}")
            print(f"Passenger: {ticket.passenger_name}")
            print(f"Total: {ticket.total_amount} {ticket.currency}")
            print(f"Itinerary: {len(ticket.itinerary)} segments")
            for seg in ticket.itinerary:
                print(f"  - {seg.airline_code}{seg.flight_number} {seg.origin}-{seg.destination} {seg.departure_date}")
        else:
            print("❌ Extraction Failed")

    # Sample 2: Marketing Email
    marketing_text = """
    Subject: Don't miss our summer sale!
    Hi John, 
    Fly to Cancun for only $299! Book now before it's too late.
    Contact us at sales@agency.com
    """
    
    print("\n--- Test Case 2: Marketing Email ---")
    category = router.classify_email(marketing_text)
    print(f"Category: {category}")

if __name__ == "__main__":
    test_ai_router()


import json
import logging
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.parsers.copa_parser import CopaParser

# Mock logger
logging.basicConfig(level=logging.INFO)

def test_copa_fuzzy():
    parser = CopaParser()
    
    # 1. SAMPLE IN SPANISH (Simulated)
    text_spanish = """
    Copa Airlines
    Itinerario para localizador de reserva KAAAF7
    
    Pasajero: ANDRES FELIPE GOMEZ (ADT)
    
    Agencia de Viajes
    GRUPO SOPORTE GLOBAL INC
    IATA: 10617390
    
    Detalles del vuelo:
    ...
    
    Boleto Electrónico para ANDRES FELIPE GOMEZ
    Número de Documento: 2302013874530
    Fecha de Emisión: 04FEB26
    
    Total Amount: USD 500.00
    Taxes: USD 50.00
    """
    
    print("\n--- TEST 1: Spanish Labels + Fuzzy ---")
    data = parser.parse(text_spanish)
    print(json.dumps(data.to_dict(), indent=2))
    
    # Validation 1
    assert data.pnr == 'KAAAF7', "Failed PNR"
    assert data.ticket_number == '2302013874530', "Failed Ticket"
    assert data.agency['iata'] == '10617390', "Failed Agency"
    assert data.fares['total_amount'] == '500.00', "Failed Total"

    # 2. SAMPLE RAW / NO LABELS (Fuzzy Only)
    text_fuzzy = """
    ...
    Grand Total: USD 1,234.56
    ...
    Some text
    2309876543210
    Some text
    ...
    IATA 99999999
    ...
    05MAR26
    """
    
    print("\n--- TEST 2: Fuzzy Only (No Labels) ---")
    data_fuzzy = parser.parse(text_fuzzy)
    print(json.dumps(data_fuzzy.to_dict(), indent=2))
    
    # Validation 2
    assert data_fuzzy.ticket_number == '2309876543210', "Failed Fuzzy Ticket"
    assert data_fuzzy.fares['total_amount'] == '1234.56', "Failed Fuzzy Total"
    # Agency extraction usually requires IATA label, but we added loose one.
    assert data_fuzzy.agency['iata'] == '99999999', "Failed Fuzzy Agency"

if __name__ == "__main__":
    try:
        test_copa_fuzzy()
        print("\n✅ ALL TESTS PASSED")
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
    except Exception as e:
        print(f"\n❌ ERROR: {e}")

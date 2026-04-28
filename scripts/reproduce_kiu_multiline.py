
import sys
import os
import logging

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.parsers.kiu_parser import KIUParser

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_kiu_multiline():
    parser = KIUParser()
    
    # Simulate Ticket with Multiline Layout (Common in Automation/HTML-to-text)
    text = """
    COMPAÑIA: CONVIASA
    
    FECHA DE EMISION:
    05 FEB 2026
    
    AGENTE EMISOR:
    BLA12345
    
    DIRECCION:
    PRINCIPAL AV VENEZUELA
    
    TICKET NUMBER:
    308-0201387528
    
    IATA:
    99999999
    
    PASAJERO:
    PEREZ/JUAN
    
    ISSUING AIRLINE:
    CONVIASA
    """
    
    print("--- TESTING KIU MULTILINE EXTRACTION ---")
    data = parser.parse(text)
    
    print(f"Fecha Emisión: {data.issue_date}")
    print(f"Agente: {data.agency.get('nombre')}")
    print(f"Dirección: {data.agency.get('direccion')}")
    print(f"IATA: {data.agency.get('iata')}")
    print(f"Boleto: {data.ticket_number}")
    
    # Assertions
    assert data.issue_date == '05 FEB 2026' or data.issue_date == '05FEB26', f"Failed Date: {data.issue_date}"
    assert data.agency.get('nombre') == 'BLA12345', f"Failed Agent: {data.agency.get('nombre')}"
    assert data.agency.get('direccion') == 'PRINCIPAL AV VENEZUELA', f"Failed Address: {data.agency.get('direccion')}"
    
    print("\n[SUCCESS] All multiline fields extracted correctly.")

if __name__ == "__main__":
    test_kiu_multiline()

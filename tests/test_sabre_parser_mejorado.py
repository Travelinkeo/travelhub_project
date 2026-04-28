
from core.ticket_parser import _parse_sabre_ticket


def test_parse_sabre_ticket_mejorado():
    plain_text = """
ETICKET RECEIPT
Prepared For JUAREZ/RAUL [AS639110]
Reservation Code ABC123
Issue Date 13 Aug 25
Ticket Number 0457281019415
Issuing Airline SAMPLE AIRLINE
Issuing Agent AGENTE 123
Itinerary Details
13 Aug 25
AA123
CARACAS, VENEZUELA
BOGOTA, COLOMBIA
08:00
10:00
Cabin Economy
Baggage Allowance 1PC
Please contact your travel arranger
"""
    parsed_data = _parse_sabre_ticket(plain_text)

    assert parsed_data is not None
    assert parsed_data['SOURCE_SYSTEM'] == 'SABRE'

    # Check normalized fields
    normalized = parsed_data.get('normalized', {})
    assert normalized.get('passenger_name') == 'RAUL JUAREZ'
    assert normalized.get('ticket_number') == '0457281019415'
    assert normalized.get('reservation_code') == 'ABC123'
    assert normalized.get('airline_name') == 'SAMPLE AIRLINE'
    assert normalized.get('issuing_agent') == 'AGENTE 123'
    assert normalized.get('issuing_date_iso') == '2025-08-13'
    
    # Check flight details
    segments = normalized.get('segments', [])
    assert len(segments) == 1
    segment = segments[0]
    assert segment.get('flight_number') == 'AA123'
    assert segment.get('origin') == 'CARACAS, VENEZUELA'
    assert segment.get('destination') == 'BOGOTA, COLOMBIA'
    assert segment.get('departure_date_iso') == '2025-08-13'
    assert segment.get('departure_time') == '08:00'
    assert segment.get('arrival_time') == '10:00'

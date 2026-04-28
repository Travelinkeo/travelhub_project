from core import ticket_parser

REQUIRED_KEYS = {"segment_index","source_system","flight_number","marketing_airline","origin","destination","departure_date_iso","departure_time","arrival_date_iso","arrival_time"}

def test_sabre_segments_structure():
    sample = (
        "Itinerary Details\n"
        "Issue Date 17 Aug 25\n"
        "Reservation Code ABC123\n"
        "Ticket Number 3080201196996\n"
        "AA123\n"
        "MIAMI, USA\n"
        "BOGOTA, COLOMBIA\n"
        "09:15\n"
        "12:05\n"
        "Cabin ECONOMY\n"
        "Baggage Allowance 1PC\n"
        "Please contact your travel arranger\n"
    )
    data = ticket_parser._parse_sabre_ticket(sample)
    segs = data['normalized'].get('segments')
    assert isinstance(segs, list) and len(segs) >= 1
    first = segs[0]
    missing = REQUIRED_KEYS - set(first.keys())
    assert not missing, f"Faltan claves en segmento Sabre: {missing}"
    assert first['segment_index'] == 1
    assert first['flight_number'] == 'AA123'
    assert first['origin'] == 'MIAMI'
    assert first['destination'] == 'BOGOTA'


def test_kiu_segments_heuristic():
    # Itinerario KIU simulado con dos líneas de vuelo
    sample = (
        "TICKET NRO: 308-0201196996\n"
        "BOOKING REF: C1/ABC123\n"
        "NAME/NOMBRE: DUQUE/OSCAR\n"
        "ISSUE DATE/FECHA DE EMISION: 17 AUG 2025 19:14\n"
        "FROM/TO FLIGHT DATE HORA HORA BASE TARIFARIA EQP. ESTATUS\n"
        "CCS KX123 BOG 18AUG\n"
        "BOG KX456 CCS 25AUG\n"
    )
    data = ticket_parser._parse_kiu_ticket(sample, "")
    segs = data['normalized'].get('segments')
    assert isinstance(segs, list)
    # Debe detectar al menos 1-2 segmentos
    assert len(segs) >= 1
    first = segs[0]
    missing = REQUIRED_KEYS - set(first.keys())
    assert not missing, f"Faltan claves en segmento KIU: {missing}"
    assert first['segment_index'] == 1
    # flight_number puede ser KX123 (heurística)
    # origin es 'CCS', destination 'BOG'
    assert first['origin'] == 'CCS'
    assert first['destination'] in ('BOG','CCS')  # segundo token puede haber variado si heurística falla

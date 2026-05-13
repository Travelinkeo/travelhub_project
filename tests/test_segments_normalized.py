from apps.automation.parsers.kiu_parser import KIUParser
from apps.automation.parsers.legacy.sabre_parser import SabreParser

REQUIRED_KEYS = {"aerolinea", "numero_vuelo", "origen", "destino", "fecha_salida", "hora_salida"}

def test_sabre_segments_structure():
    sample = (
        "Itinerary Details\n"
        "Issue Date 17 Aug 25\n"
        "Reservation Code ABC123\n"
        "Ticket Number 3080201196996\n"
        "1 AA 123 C 17AUG MIAMI, FL BOGOTA, CO HK1 08:00 12:00\n"
        "Baggage Allowance 1PC\n"
        "Please contact your travel arranger\n"
    )
    parser = SabreParser()
    parsed_data = parser.parse(sample)
    segs = parsed_data.flights
    assert isinstance(segs, list) and len(segs) >= 1
    first = segs[0]
    
    missing = REQUIRED_KEYS - set(first.keys())
    assert not missing, f"Faltan claves en segmento Sabre: {missing}"
    
    assert first['numero_vuelo'] == 'AA123'
    assert first['origen'] == 'MIAMI'
    assert first['destino'] == 'BOGOTA'


def test_kiu_segments_structure():
    # Itinerario KIU simplificado con V0 (Conviasa) para asegurar detección
    sample = (
        "TICKET NRO: 308-0201196996\n"
        "NAME/NOMBRE: DUQUE/OSCAR\n"
        "ISSUE DATE/FECHA DE EMISION: 17 AUG 2025\n"
        "FROM/TO FLIGHT CLASS DATE DEP ARR\n"
        "CCS V01187 G 18AUG 0850 0950\n"
        "BOG\n"
    )
    parser = KIUParser()
    parsed_data = parser.parse(sample)
    segs = parsed_data.flights
    assert isinstance(segs, list)
    # Debe detectar al menos 1 segmento
    assert len(segs) >= 1
    first = segs[0]
    
    missing = REQUIRED_KEYS - set(first.keys())
    assert not missing, f"Faltan claves en segmento KIU: {missing}"
    
    assert first['aerolinea'] == 'CONVIASA'
    assert first['origen'] == 'CCS'
    assert first['destino'] == 'BOG'

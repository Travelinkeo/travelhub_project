import pytest

from core import ticket_parser


@pytest.mark.skip(reason="KIU parser is a placeholder")
def test_kiu_normalized_block_minimal():
    sample = (
        "TICKET NRO: 308-0201196996\n"
        "BOOKING REF: C1/ABC123\n"
        "NAME/NOMBRE: DUQUE/OSCAR\n"
        "ISSUE DATE/FECHA DE EMISION: 17 AUG 2025 19:14\n"
        "ISSUE AGENT: AG1234\n"
        "ISSUING AIRLINE: RUTAS AEREAS DE VENEZUELA RAV, SA\n"
        "AIR FARE: USD 170.00\n"
        "TOTAL: USD 210.50\n"
        "FROM/TO FLIGHT DATE HORA HORA BASE TARIFARIA EQP. ESTATUS\n"
        "CCS M123 CCS 17AUG\n"
    )
    data = ticket_parser._parse_kiu_ticket(sample, "")
    assert 'normalized' in data, 'Debe existir bloque normalized'
    n = data['normalized']
    assert n.get('source_system') == 'KIU'
    assert n.get('ticket_number') == data.get('NUMERO_DE_BOLETO')
    assert n.get('reservation_code') in ('ABC123', 'C1/ABC123')  # depende de heurística
    assert n.get('issuing_date_iso') == '2025-08-17'
    assert n.get('fare_currency') == 'USD'
    assert n.get('total_currency') == 'USD'


def test_sabre_normalized_block_minimal():
    sample = (
        "Itinerary Details\n"
        "Issue Date 17 Aug 25\n"
        "Reservation Code ABC123\n"
        "Ticket Number 3080201196996\n"
        "Issuing Airline EXAMPLE AIRLINE\n"
        "Issuing Agent AG5678\n"
        "Fare USD 123.45\n"
        "Total USD 150.60\n"
        "Please contact your travel arranger\n"
    )
    data = ticket_parser._parse_sabre_ticket(sample)
    assert 'normalized' in data, 'Debe existir bloque normalized'
    n = data['normalized']
    assert n.get('source_system') == 'SABRE'
    assert n.get('ticket_number') == data.get('numero_boleto')
    assert n.get('reservation_code') == data.get('codigo_reservacion')
    assert n.get('issuing_date_iso') is not None
    assert n.get('fare_currency') == 'USD'
    assert n.get('total_currency') == 'USD'
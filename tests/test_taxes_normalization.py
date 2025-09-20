from core import ticket_parser


def test_kiu_taxes_normalization():
    sample = (
        "TICKET NRO: 308-0201196996\n"
        "BOOKING REF: C1/ABC123\n"
        "NAME/NOMBRE: DUQUE/OSCAR\n"
        "ISSUE DATE/FECHA DE EMISION: 17 AUG 2025 19:14\n"
        "AIR FARE: USD 170.00\n"
        "TOTAL: USD 210.50\n"
    )
    data = ticket_parser._parse_kiu_ticket(sample, "")
    n = data['normalized']
    assert n.get('taxes_currency') == 'USD'
    # 210.50 - 170.00 = 40.50
    assert n.get('taxes_amount') in ('40.50', '40.5')


def test_sabre_taxes_normalization():
    sample = (
        "Itinerary Details\n"
        "Issue Date 17 Aug 25\n"
        "Reservation Code ABC123\n"
        "Ticket Number 3080201196996\n"
        "Fare USD 123.45\n"
        "Total USD 150.60\n"
        "Please contact your travel arranger\n"
    )
    data = ticket_parser._parse_sabre_ticket(sample)
    n = data['normalized']
    assert n.get('taxes_currency') == 'USD'
    # 150.60 - 123.45 = 27.15
    assert n.get('taxes_amount') in ('27.15', '27.1', '27.150')  # tolerar formato

from core import ticket_parser


def test_sabre_two_segment_layover():
    # Segmento 1: 09:00 -> 10:30  (duración 90)
    # Segmento 2: sale 12:00 mismo día (layover 90 min)
    sample = (
        "Itinerary Details\n"
        "Issue Date 17 Aug 25\n"
        "Reservation Code ABC123\n"
        "Ticket Number 3080201196996\n"
        # Primer vuelo
        "AA123\n"
        "MIAMI, USA\n"
        "CHARLOTTE, USA\n"
        "09:00\n"
        "10:30\n"
        "Cabin ECONOMY\n"
        "Baggage Allowance 1PC\n"
        # Segundo vuelo
        "AA456\n"
        "CHARLOTTE, USA\n"
        "NEW YORK, USA\n"
        "12:00\n"
        "14:15\n"
        "Cabin ECONOMY\n"
        "Baggage Allowance 1PC\n"
        "Please contact your travel arranger\n"
    )
    data = ticket_parser._parse_sabre_ticket(sample)
    segs = data['normalized']['segments']
    assert len(segs) >= 2
    first, second = segs[0], segs[1]
    assert first['duration_minutes'] == 90
    assert second['duration_minutes'] == ( (14*60+15) - (12*60) )  # 135
    assert second['layover_minutes'] == 90  # 10:30 -> 12:00 = 90

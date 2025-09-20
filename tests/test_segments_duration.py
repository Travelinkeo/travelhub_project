from core import ticket_parser


def test_sabre_segment_duration_same_day():
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
	segs = data['normalized']['segments']
	assert segs and segs[0]['duration_minutes'] == ( (12*60+5) - (9*60+15) )  # 170 minutos


def test_sabre_segment_duration_cross_midnight():
	sample = (
		"Itinerary Details\n"
		"Issue Date 17 Aug 25\n"
		"Reservation Code ABC123\n"
		"Ticket Number 3080201196996\n"
		"AA124\n"
		"MIAMI, USA\n"
		"MADRID, ESPAÑA\n"
		"23:30\n"
		"05:50\n"
		"Cabin ECONOMY\n"
		"Baggage Allowance 1PC\n"
		"Please contact your travel arranger\n"
	)
	data = ticket_parser._parse_sabre_ticket(sample)
	seg = data['normalized']['segments'][0]
	# Cruza medianoche: (23:30 -> 05:50) = 6h20 = 380 min + 24h? No, lógica añade +1 día solo si arr_dt < dep_dt
	# 23:30 a 05:50 => arr_dt < dep_dt inicialmente, se suma +1 día: duración = (24:00-23:30)=30m + 5h50 = 6h20=380m
	assert seg['duration_minutes'] == 380

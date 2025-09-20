from core import ticket_parser


def test_amount_consistency_ok_kiu():
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
    assert n['taxes_amount'] in ('40.50','40.5')
    assert n.get('amount_consistency') == 'OK'
    assert n.get('amount_difference') in ('0.00','0')


def test_amount_consistency_mismatch_sabre():
    # Suministramos taxes_amount explícito incorrecto para forzar MISMATCH
    raw = {
        'SOURCE_SYSTEM': 'SABRE',
        'numero_boleto': '3080201196996',
        'codigo_reservacion': 'ABC123',
        'preparado_para': 'DOE/JOHN',
        'fecha_emision_iso': '2025-08-17',
        'fare_currency': 'USD',
        'fare_amount': '100.00',
        'taxes_currency': 'USD',
        'taxes_amount': '40.60',  # Reportado incorrecto
        'total_currency': 'USD',
        'total_amount': '160.60',  # Esperado taxes sería 60.60
        'vuelos': []
    }
    ticket_parser.normalize_common_fields(raw)
    n2 = raw['normalized']
    assert n2.get('amount_consistency') == 'MISMATCH'
    assert n2.get('taxes_amount_expected') == '60.60'
    assert n2.get('taxes_difference') in ('-20.00','-20.00')


def test_amount_consistency_tolerance():
    # Fare + taxes difiere del total en 0.01 -> debe considerarse OK
    raw = {
        'SOURCE_SYSTEM': 'SABRE',
        'numero_boleto': '3080201196997',
        'codigo_reservacion': 'DEF456',
        'preparado_para': 'TEST/USER',
        'fecha_emision_iso': '2025-08-17',
        'fare_currency': 'USD',
        'fare_amount': '200.00',
        'taxes_currency': 'USD',
        'taxes_amount': '49.99',  # Reportado
        'total_currency': 'USD',
        'total_amount': '250.00',  # Esperado taxes sería 50.00 (diff 0.01 tolerado)
        'vuelos': []
    }
    ticket_parser.normalize_common_fields(raw)
    n = raw['normalized']
    assert n.get('amount_consistency') == 'OK'
    # taxes_difference debería ser -0.01
    assert n.get('taxes_difference') in ('-0.01','-0.010')

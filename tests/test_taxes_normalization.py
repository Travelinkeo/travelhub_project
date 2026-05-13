from apps.automation.parsers.kiu_parser import KIUParser
from apps.automation.parsers.legacy.sabre_parser import SabreParser
from decimal import Decimal

def test_kiu_taxes_normalization():
    sample = (
        "TICKET NRO: 308-0201196996\n"
        "BOOKING REF: C1/ABC123\n"
        "NAME/NOMBRE: DUQUE/OSCAR\n"
        "ISSUE DATE/FECHA DE EMISION: 17 AUG 2025 19:14\n"
        "AIR FARE: USD 170.00\n"
        "TOTAL: USD 210.50\n"
    )
    parser = KIUParser()
    parsed_data = parser.parse(sample)
    d = parsed_data.to_dict()
    
    # 210.50 - 170.00 = 40.50
    # Usar Decimal para evitar problemas de formato de string ('210.5' vs '210.50')
    assert Decimal(d.get('IMPUESTOS')) == Decimal('40.50')
    assert Decimal(d.get('TARIFA_IMPORTE')) == Decimal('170.00')
    assert Decimal(d.get('TOTAL_IMPORTE')) == Decimal('210.50')


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
    parser = SabreParser()
    parsed_data = parser.parse(sample)
    d = parsed_data.to_dict()
    
    # 150.60 - 123.45 = 27.15
    assert Decimal(d.get('IMPUESTOS')) == Decimal('27.15')
    assert Decimal(d.get('TARIFA_IMPORTE')) == Decimal('123.45')
    assert Decimal(d.get('TOTAL_IMPORTE')) == Decimal('150.60')

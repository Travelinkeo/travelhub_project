import sys, os
import re
import pytest

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(PROJECT_ROOT)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from core.pdf_generator import generate_ticket_pdf

@pytest.mark.parametrize("raw_name,expected", [
    ("DUQUE ECHEVERRY/OSCA (CIUDAD DE PANAMA)", "DUQUE ECHEVERRY/OSCA"),
    ("DUQUE ECHEVERRY/OSCA (CIUDAD DE PANAMA) (PANAMA)", "DUQUE ECHEVERRY/OSCA"),
    ("DUQUE ECHEVERRY/OSCA", "DUQUE ECHEVERRY/OSCA"),
])
def test_pdf_name_sanitization(raw_name, expected):
    data = {
        'SOURCE_SYSTEM': 'KIU',
        'SOLO_NOMBRE_PASAJERO': 'OSCA',
        'SOLO_CODIGO_RESERVA': 'ABC123',
        'NUMERO_DE_BOLETO': '0190000000000',
        'NOMBRE_DEL_PASAJERO': raw_name,
        'CODIGO_IDENTIFICACION': 'IDTEST',
        'FECHA_DE_EMISION': '18 AUG 2023 19:12',
        'AGENTE_EMISOR': 'AGT123',
        'NOMBRE_AEROLINEA': 'SATENA S.A',
        'DIRECCION_AEROLINEA': 'AV PRINCIPAL 123',
        'TARIFA': 'USD 100.00',
        'IMPUESTOS': 'AK 10.00',
        'TOTAL': 'USD 110.00',
        'ItinerarioFinalLimpio': 'CARACAS 9R8901 25AUG 0945 1046',
    }
    pdf_bytes, filename = generate_ticket_pdf(data)
    # El PDF se genera; verificamos que el nombre saneado no incluya parentesis
    # (Chequeo indirecto: el data mutado en generate_ticket_pdf ya está limpio)
    assert data['NOMBRE_DEL_PASAJERO'] == expected
    # Validación ligera de que se generó algo
    assert isinstance(pdf_bytes, (bytes, bytearray)) and len(pdf_bytes) > 1000

import pytest
import sys, os
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
from core import ticket_parser

SAMPLE_KIU_TEXT = """
ISSUING AIRLINE/LINEA AEREA EMISORA: RUTAS AEREAS DE VENEZUELA RAV, SA ISSUE DATE/FECHA DE EMISION: 17 AUG 2025 19:14
ADDRESS/DIRECCION: AV. PRINCIPAL EDIF 123
TICKET NRO: 364-0260391273
""".strip()

EXPECTED_NAME = "RUTAS AEREAS DE VENEZUELA RAV, SA"

def test_nombre_aerolinea_no_se_contamina():
    nombre = ticket_parser._get_nombre_aerolinea(SAMPLE_KIU_TEXT)
    assert nombre == EXPECTED_NAME

@pytest.mark.parametrize(
    "line,expected",
    [
        ("ISSUING AIRLINE: RUTAS AEREAS DE VENEZUELA RAV, SA ADDRESS", EXPECTED_NAME),
        ("ISSUING AIRLINE: RUTAS AEREAS DE VENEZUELA RAV, SA TICKET", EXPECTED_NAME),
    ("ISSUING AIRLINE: RUTAS AEREAS DE VENEZUELA RAV, SA ISSUE DATE/FECHA DE EMISION: 17 AUG 2025 19:14", EXPECTED_NAME),
    ("ISSUING AIRLINE: RUTAS AEREAS DE VENEZUELA RAV, SA BOOKING REF/CODIGO DE RESERVA: C1/ABC123", EXPECTED_NAME),
    ("ISSUING AIRLINE: RUTAS AEREAS DE VENEZUELA RAV, SA (ALGUN TEXTO EXTRA)", EXPECTED_NAME),
    ],
)
def test_cortes_por_tokens(line, expected):
    nombre = ticket_parser._get_nombre_aerolinea(line)
    assert nombre == expected

import sys, os, re
import pytest

# Ensure project root on path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(PROJECT_ROOT)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from core.ticket_parser import _get_nombre_completo_pasajero, _get_solo_nombre_pasajero

@pytest.mark.parametrize(
    "block,expected_full,expected_short",
    [
        (
            "TORRES DEL RIO                                 NAME/NOMBRE:  DUQUE ECHEVERRY/OSCA\n CIUDAD DE PANAMA, PANAMA                  FOID/D.IDENTIDAD: IDVCI24168987",
            "DUQUE ECHEVERRY/OSCA",
            "OSCA",
        ),
        (
            "DORAL                                          NAME/NOMBRE:  DUQUE ECHEVERRY/OSCA\n FLORIDA 33166, UNITED STATES              FOID/D.IDENTIDAD: IDEPPE151144",
            "DUQUE ECHEVERRY/OSCA",
            "OSCA",
        ),
    ],
)
def test_pasenger_name_not_contaminated_with_city(block, expected_full, expected_short):
    full = _get_nombre_completo_pasajero(block)
    assert full == expected_full, f"Nombre completo contaminado: {full}"
    solo = _get_solo_nombre_pasajero(full)
    assert solo == expected_short, f"Nombre corto incorrecto: {solo}"


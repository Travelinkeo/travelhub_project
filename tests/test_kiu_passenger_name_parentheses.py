import sys, os
import pytest

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(PROJECT_ROOT)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from core.ticket_parser import _get_nombre_completo_pasajero, _get_solo_nombre_pasajero

@pytest.mark.parametrize(
    "line,expected_full,expected_short",
    [
        (
            # Contaminación con ciudad entre paréntesis
            "NAME/NOMBRE:  DUQUE ECHEVERRY/OSCA (CIUDAD DE PANAMA) FOID/D.IDENTIDAD: IDVCI24168987",
            "DUQUE ECHEVERRY/OSCA",
            "OSCA",
        ),
        (
            # Contaminación con estado / país
            "NAME/NOMBRE:  DUQUE ECHEVERRY/OSCA (FLORIDA) TELEPHONE/TELEFONO: 0000",
            "DUQUE ECHEVERRY/OSCA",
            "OSCA",
        ),
        (
            # Sin contaminación
            "NAME/NOMBRE:  PEREZ LOPEZ/JUAN",
            "PEREZ LOPEZ/JUAN",
            "JUAN",
        ),
    ],
)
def test_parentheses_city_contamination(line, expected_full, expected_short):
    full = _get_nombre_completo_pasajero(line)
    assert full == expected_full, f"Nombre extraído incorrecto: {full}"
    solo = _get_solo_nombre_pasajero(full)
    assert solo == expected_short

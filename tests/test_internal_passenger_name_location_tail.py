import os, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from core.ticket_parser import _get_nombre_completo_pasajero, _get_solo_nombre_pasajero

def build_text(name_line_tail: str) -> str:
    return f"NAME/NOMBRE:  {name_line_tail}\nFOID/D.IDENTIDAD: IDTEST123"

def test_internal_removes_ciudad_de_panama_tail():
    text = build_text("DUQUE ECHEVERRY/OSCA CIUDAD DE PANAMA PANAMA")
    full = _get_nombre_completo_pasajero(text)
    assert full == "DUQUE ECHEVERRY/OSCA"
    solo = _get_solo_nombre_pasajero(full)
    assert solo == "OSCA"

def test_internal_keeps_normal_name():
    text = build_text("PEREZ/JOSE")
    full = _get_nombre_completo_pasajero(text)
    assert full == "PEREZ/JOSE"


def test_internal_removes_united_states_tail():
    text = build_text("ROJAS/EMMA UNITED STATES")
    full = _get_nombre_completo_pasajero(text)
    assert full == "ROJAS/EMMA"
    solo = _get_solo_nombre_pasajero(full)
    assert solo == "EMMA"

def test_internal_removes_florida_tail():
    text = build_text("DUQUE ECHEVERRY/OSCA FLORIDA")
    full = _get_nombre_completo_pasajero(text)
    assert full == "DUQUE ECHEVERRY/OSCA"
    solo = _get_solo_nombre_pasajero(full)
    assert solo == "OSCA"

import os, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from external_ticket_generator.KIU.mi_proyecto_final.mi_proyecto_final.main import sanitize_nombre_completo_pasajero

def test_external_removes_trailing_florida():
    raw = "DUQUE ECHEVERRY/OSCA FLORIDA"
    cleaned = sanitize_nombre_completo_pasajero(raw)
    assert cleaned == "DUQUE ECHEVERRY/OSCA"

def test_external_keeps_valid():
    raw = "PEREZ/JOSE"
    assert sanitize_nombre_completo_pasajero(raw) == "PEREZ/JOSE"

import pytest
import sys
from pathlib import Path

# Asegurar que el root del proyecto está en sys.path para importar el módulo externo
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from external_ticket_generator.KIU.mi_proyecto_final.mi_proyecto_final.main import get_codigo_identificacion

def test_external_codigo_identificacion_inline():
    texto = ("TORRES DEL RIO                                 NAME/NOMBRE:  DUQUE ECHEVERRY/OSCA\n"
             " FLORIDA 33166, UNITED STATES              FOID/D.IDENTIDAD: IDEPPE151144 OFFICE ID: US-16445-0\n"
             " TELEPHONE/TELEFONO: (786) 703 5079")
    assert get_codigo_identificacion(texto) == "IDEPPE151144"

@pytest.mark.parametrize("cadena,esperado", [
    ("RANDOM /D.IDENTIDAD: FOID: DUPLICATE777 ADDRESS", "DUPLICATE777"),
    ("XYZ FOID: XYZ999 RIF 123", "XYZ999"),
])
def test_external_codigo_identificacion_variantes(cadena, esperado):
    assert get_codigo_identificacion(cadena) == esperado

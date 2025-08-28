import sys, os, pytest, re

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from core.ticket_parser import _get_codigo_identificacion as internal_get_id
from external_ticket_generator.KIU.mi_proyecto_final.mi_proyecto_final.main import get_codigo_identificacion as external_get_id

RAW_TEXT_TEMPLATE = """
FOID/D.IDENTIDAD: {value}\nOTHER LINE
"""

@pytest.mark.parametrize("raw,expected", [
    ("/D.IDENTIDAD: IDEPPE151144", "IDEPPE151144"),
    ("D.IDENTIDAD: ABC12345", "ABC12345"),
    ("FOID: XYZ999", "XYZ999"),
    ("/D.IDENTIDAD: FOID: DUPLICATE777", "DUPLICATE777"),
])
def test_external_normalization(raw, expected):
    text = RAW_TEXT_TEMPLATE.format(value=raw)
    assert external_get_id(text) == expected

@pytest.mark.parametrize("raw,expected", [
    ("/D.IDENTIDAD: IDEPPE151144", "IDEPPE151144"),
    ("D.IDENTIDAD: ABC12345", "ABC12345"),
    ("FOID: XYZ999", "XYZ999"),
    ("/D.IDENTIDAD: FOID: DUPLICATE777", "DUPLICATE777"),
])
def test_internal_normalization(raw, expected):
    text = RAW_TEXT_TEMPLATE.format(value=raw)
    assert internal_get_id(text) == expected

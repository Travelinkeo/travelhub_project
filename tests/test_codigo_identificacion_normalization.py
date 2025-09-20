import os

import pytest

from core.identification_utils import extract_codigo_identificacion_anywhere as internal_get_id

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))


# from external_ticket_generator.KIU.mi_proyecto_final.mi_proyecto_final.main import get_codigo_identificacion as external_get_id

RAW_TEXT_TEMPLATE = """
FOID/D.IDENTIDAD: {value}\nOTHER LINE
"""

# @pytest.mark.parametrize("raw,expected", [
#     ("/D.IDENTIDAD: IDEPPE151144", "IDEPPE151144"),
#     ("D.IDENTIDAD: ABC12345", "ABC12345"),
#     ("FOID: XYZ999", "XYZ999"),
#     ("/D.IDENTIDAD: FOID: DUPLICATE777", "DUPLICATE777"),
# ])
# def test_external_normalization(raw, expected):
#     text = RAW_TEXT_TEMPLATE.format(value=raw)
#     assert external_get_id(text) == expected

@pytest.mark.parametrize("raw,expected", [
    ("/D.IDENTIDAD: IDEPPE151144", "IDEPPE151144"),
    ("D.IDENTIDAD: ABC12345", "ABC12345"),
    ("FOID: XYZ999", "XYZ999"),
    ("/D.IDENTIDAD: FOID: DUPLICATE777", "DUPLICATE777"),
])
def test_internal_normalization(raw, expected):
    text = RAW_TEXT_TEMPLATE.format(value=raw)
    assert internal_get_id(text) == expected

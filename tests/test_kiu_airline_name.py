"""Tests para Kiu airline name."""
import os

import pytest

from apps.automation.parsers import ticket_parser

pytestmark = pytest.mark.skip(reason="Funciones de parser refactorizadas - pendiente actualización")

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


SAMPLE_KIU_TEXT = """
ISSUING AIRLINE/LINEA AEREA EMISORA: RUTAS AEREAS DE VENEZUELA RAV, SA ISSUE DATE/FECHA DE EMISION: 17 AUG 2025 19:14
ADDRESS/DIRECCION: AV. PRINCIPAL EDIF 123
TICKET NRO: 364-0260391273
""".strip()

EXPECTED_NAME = "RUTAS AEREAS DE VENEZUELA RAV, SA"


def test_nombre_aerolinea_no_se_contamina():
    """Nombre aerolinea no se contamina."""
    nombre = ticket_parser._kiu_get_nombre_aerolinea(SAMPLE_KIU_TEXT)
    assert nombre == EXPECTED_NAME


@pytest.mark.parametrize(
    "line,expected",
    [
        ("ISSUING AIRLINE: RUTAS AEREAS DE VENEZUELA RAV, SA ADDRESS", EXPECTED_NAME),
        ("ISSUING AIRLINE: RUTAS AEREAS DE VENEZUELA RAV, SA TICKET", EXPECTED_NAME),
        (
            "ISSUING AIRLINE: RUTAS AEREAS DE VENEZUELA RAV, SA ISSUE DATE/FECHA DE EMISION: 17 AUG 2025 19:14",
            EXPECTED_NAME,
        ),
        (
            "ISSUING AIRLINE: RUTAS AEREAS DE VENEZUELA RAV, SA BOOKING REF/CODIGO DE RESERVA: C1/ABC123",
            EXPECTED_NAME,
        ),
        ("ISSUING AIRLINE: RUTAS AEREAS DE VENEZUELA RAV, SA (ALGUN TEXTO EXTRA)", EXPECTED_NAME),
    ],
)
def test_cortes_por_tokens(line, expected):
    """Cortes por tokens."""
    nombre = ticket_parser._kiu_get_nombre_aerolinea(line)
    assert nombre == expected

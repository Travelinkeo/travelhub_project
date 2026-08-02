import pytest

from apps.automation.parsers.kiu_parser import KIUParser

SAMPLE_KIU_TEXT = """
ISSUING AIRLINE/LINEA AEREA EMISORA: RUTAS AEREAS DE VENEZUELA RAV, SA ISSUE DATE/FECHA DE EMISION: 17 AUG 2025 19:14
ADDRESS/DIRECCION: AV. PRINCIPAL EDIF 123
TICKET NRO: 364-0260391273
""".strip()

EXPECTED_NAME = "RUTAS AEREAS DE VENEZUELA"


@pytest.fixture
def kiu_parser():
    return KIUParser()


def test_nombre_aerolinea_no_se_contamina(kiu_parser):
    """test_nombre_aerolinea_no_se_contamina."""
    nombre = kiu_parser._extract_airline(SAMPLE_KIU_TEXT)
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
def test_cortes_por_tokens(kiu_parser, line, expected):
    """test_cortes_por_tokens."""
    nombre = kiu_parser._extract_airline(line)
    assert nombre == expected

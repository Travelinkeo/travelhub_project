import pytest

from apps.automation.parsers.amadeus_parser import AmadeusParser as SabreParser
from apps.automation.parsers.kiu_parser import KIUParser


@pytest.fixture
def kiu_parser():
    return KIUParser()


@pytest.fixture
def sabre_parser():
    return SabreParser()


def test_kiu_fecha_emision_iso_present(kiu_parser):
    """test_kiu_fecha_emision_iso_present."""
    sample = "ISSUE DATE/FECHA DE EMISION: 17 AUG 2025 19:14\nOTHER LINE"
    fecha = kiu_parser._extract_issue_date(sample)
    assert fecha != "No encontrado"
    iso = kiu_parser.normalize_date(fecha)
    assert iso == "2025-08-17"


def test_sabre_fecha_emision_iso_present(sabre_parser):
    """test_sabre_fecha_emision_iso_present."""
    sample = (
        "Itinerary Details\n...\nIssue Date 17 Aug 25\n...\nPlease contact your travel arranger"
    )
    fecha = sabre_parser.extract_field(
        sample,
        [
            r"(?:Issue Date|Fecha de Emisi[óo]n|FECHA DE EMISI[ÓO]N)\s*[:\t\s]*([^\n]+)",
            r"emisi[^\n]*?([0-9]{1,2}[A-Z]{3}[0-9]{2,4})",
        ],
    )
    assert fecha != "No encontrado"
    iso = sabre_parser.normalize_date(fecha)
    assert iso is not None
    assert iso.startswith("202")

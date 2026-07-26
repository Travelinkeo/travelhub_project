import os

import pytest

from apps.automation.parsers.adapter import _register_parsers
from apps.automation.parsers.registry import registry

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
# Fixtures live in tests/fixtures/ (no external_ticket_generator dependency)
SABRE_DIR = os.path.join(BASE_DIR, "fixtures")

# Sample files we expect to exist
SINGLE_FILE = "sabre_0457281019415_fixture.txt"
MULTI_FILE = "sabre_0577280309142_fixture.txt"


def read_ticket(filename: str):
    """read_ticket."""
    path = os.path.join(SABRE_DIR, filename)
    with open(path, encoding="utf-8", errors="ignore") as f:
        return f.read()


def get_parsed_dto(text: str):
    """get_parsed_dto."""
    _register_parsers()
    parser = registry.find_parser(text)
    assert parser is not None, "No se encontró parser compatible con Sabre"
    parsed_data = parser.parse(text)
    return parsed_data.to_pydantic()


@pytest.mark.django_db
def test_single_segment_sabre():
    """test_single_segment_sabre."""
    text = read_ticket(SINGLE_FILE)
    res = get_parsed_dto(text)

    assert len(res.boletos) == 1
    boleto = res.boletos[0]

    assert boleto.source_system == "SABRE"
    assert boleto.codigo_identificacion == "AS639110"
    assert boleto.fecha_emision == "2025-08-13"
    assert boleto.numero_boleto == "0457281019415"
    assert boleto.codigo_reserva == "ABC123"

    assert len(boleto.itinerario) == 1
    vuelo = boleto.itinerario[0]
    assert "VENEZUELA" in vuelo.origen.upper()
    assert "COLOMBIA" in vuelo.destino.upper()
    assert vuelo.fecha_salida == "13 Aug 25"
    assert vuelo.hora_salida == "08:00"
    assert vuelo.hora_llegada == "10:00"


@pytest.mark.django_db
def test_multi_segment_sabre():
    """test_multi_segment_sabre."""
    text = read_ticket(MULTI_FILE)
    res = get_parsed_dto(text)

    assert len(res.boletos) == 1
    boleto = res.boletos[0]

    assert boleto.source_system == "SABRE"
    assert boleto.codigo_identificacion == "164271115"
    assert boleto.fecha_emision == "2025-02-25"
    assert boleto.numero_boleto == "0577280309142"
    assert boleto.codigo_reserva == "SGWFJU"

    assert len(boleto.itinerario) >= 4
    expected_countries = [
        ("VENEZUELA", "COLOMBIA"),
        ("COLOMBIA", "PERU"),
        ("PERU", "CHILE"),
        ("CHILE", "VENEZUELA"),
    ]
    for i, vuelo in enumerate(boleto.itinerario):
        assert vuelo.fecha_salida
        assert vuelo.fecha_llegada
        assert expected_countries[i][0] in vuelo.origen.upper()
        assert expected_countries[i][1] in vuelo.destino.upper()

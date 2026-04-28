import pytest

from core import ticket_parser


@pytest.mark.skip(reason="KIU parser is a placeholder")
def test_kiu_fecha_emision_iso_present():
    # Ejemplo simplificado de línea KIU con ISSUE DATE/FECHA DE EMISION
    sample = "ISSUE DATE/FECHA DE EMISION: 17 AUG 2025 19:14\nOTHER LINE"
    data = ticket_parser._parse_kiu_ticket(sample, "")
    assert 'FECHA_DE_EMISION' in data
    assert data['FECHA_DE_EMISION'] != 'No encontrado'
    assert 'fecha_emision_iso' in data and data['fecha_emision_iso'] is not None
    assert data['fecha_emision_iso'] == '2025-08-17'


def test_sabre_fecha_emision_iso_present():
    # Ejemplo simplificado para Sabre
    sample = "Itinerary Details\n...\nIssue Date 17 Aug 25\n...\nPlease contact your travel arranger"
    data = ticket_parser._parse_sabre_ticket(sample)
    assert 'fecha_emision_iso' in data and data['fecha_emision_iso'] is not None
    # Puede venir como 2-digit year -> string_a_fecha maneja y _fecha_a_iso equivale
    assert data['fecha_emision_iso'].startswith('202')
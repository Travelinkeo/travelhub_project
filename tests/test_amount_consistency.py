from decimal import Decimal

import pytest

from apps.automation.parsers.kiu_parser import KIUParser


@pytest.fixture
def parser():
    return KIUParser()


def test_amount_consistency_ok_kiu(parser):
    """test_amount_consistency_ok_kiu."""
    sample = (
        "TICKET NRO: 308-0201196996\n"
        "BOOKING REF: C1/ABC123\n"
        "NAME/NOMBRE: DUQUE/OSCAR\n"
        "ISSUE DATE/FECHA DE EMISION: 17 AUG 2025 19:14\n"
        "AIR FARE: USD 170.00\n"
        "TOTAL: USD 210.50\n"
    )
    a = parser._extract_amounts(sample)
    assert Decimal(a["fare_amount"]) == Decimal("170.00")
    assert Decimal(a["total_amount"]) == Decimal("210.50")
    assert Decimal(a["tax_details"]["total_taxes"]) == Decimal("40.50")
    assert a["es_remision"] is False


def test_amount_consistency_mismatch_sabre(parser):
    """test_amount_consistency_mismatch_sabre."""
    sample = "TICKET NRO: 308-0201196996\nAIR FARE: USD 100.00\nTOTAL: USD 160.60\n"
    a = parser._extract_amounts(sample)
    assert Decimal(a["fare_amount"]) == Decimal("100.00")
    assert Decimal(a["total_amount"]) == Decimal("160.60")
    assert Decimal(a["tax_details"]["total_taxes"]) == Decimal("60.60")


def test_amount_consistency_tolerance(parser):
    """test_amount_consistency_tolerance."""
    sample = "TICKET NRO: 308-0201196997\nAIR FARE: USD 200.00\nTOTAL: USD 250.00\n"
    a = parser._extract_amounts(sample)
    assert Decimal(a["fare_amount"]) == Decimal("200.00")
    assert Decimal(a["total_amount"]) == Decimal("250.00")
    assert Decimal(a["tax_details"]["total_taxes"]) == Decimal("50.00")

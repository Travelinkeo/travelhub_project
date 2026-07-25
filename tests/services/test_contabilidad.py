"""Tests para servicios de contabilidad — BCV, reportes, proveedores."""

import unittest.mock
from decimal import Decimal

import pytest

pytestmark = [pytest.mark.django_db, pytest.mark.services]


class TestBcvClient:
    """Test Bcv Client."""
    def test_obtener_tasas(self, monkeypatch):
        """Obtener tasas."""
        mock_response = unittest.mock.MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "USD": {"transferencia": 55.25, "efectivo": 55.10},
        }
        monkeypatch.setattr("apps.contabilidad.bcv_client.requests.get", lambda url, **kw: mock_response)

        from apps.contabilidad.bcv_client import obtener_tasas_bcv

        result = obtener_tasas_bcv()
        assert isinstance(result, dict)


class TestSupplierReportService:
    """Test Supplier Report Service."""
    def test_parse_report(self, monkeypatch):
        """Parse report."""
        mock_parser = unittest.mock.MagicMock()
        mock_parser.can_parse.return_value = True
        mock_parser.parse.return_value = {"status": "ok"}

        monkeypatch.setattr(
            "apps.contabilidad.supplier_report_service.parser_registry",
            unittest.mock.MagicMock(),
        )
        import apps.contabilidad.supplier_report_service as srs

        srs.parser_registry.find_parser.return_value = mock_parser

        result = srs.parse_report("test text")
        assert result is not None

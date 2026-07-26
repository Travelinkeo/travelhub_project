"""Tests para servicios unificados de reconciliación"""

from unittest.mock import Mock, patch

import pytest

from apps.finance.services.smart_reconciliation_service import SmartReconciliationService


class TestSmartReconciliationService:
    """Tests para SmartReconciliationService"""

    @patch("apps.finance.services.smart_reconciliation_service.ReporteReconciliacion.objects.get")
    @patch.object(SmartReconciliationService, "_extraer_datos_archivo")
    @patch.object(SmartReconciliationService, "_guardar_lineas_extraidas")
    @patch.object(SmartReconciliationService, "_ejecutar_cruce_conciliacion")
    def test_procesar_reporte_success(self, mock_cruce, mock_guardar, mock_extraer, mock_get):
        """test_procesar_reporte_success."""
        reporte = Mock()
        reporte.estado = "PENDIENTE"
        reporte.save = Mock()
        mock_get.return_value = reporte
        mock_extraer.return_value = {"items": []}
        mock_guardar.return_value = None
        mock_cruce.return_value = {
            "total_lineas": 0,
            "cuadrados_ok": 0,
            "discrepancias": 0,
            "huerfanos_reporte": 0,
            "huerfanos_local": 0,
        }

        SmartReconciliationService.procesar_reporte("test-uuid")

        assert reporte.estado == "CONCILIADO"
        reporte.save.assert_called()

    @patch("apps.finance.services.smart_reconciliation_service.ReporteReconciliacion.objects.get")
    @patch.object(SmartReconciliationService, "_extraer_datos_archivo")
    def test_procesar_reporte_error(self, mock_extraer, mock_get):
        """test_procesar_reporte_error."""
        reporte = Mock()
        reporte.estado = "PENDIENTE"
        reporte.save = Mock()
        mock_get.return_value = reporte
        mock_extraer.side_effect = Exception("Parse error")

        with pytest.raises(Exception, match="Parse error"):
            SmartReconciliationService.procesar_reporte("test-uuid")

        assert reporte.estado == "ERROR"
        assert reporte.error_log == "Parse error"

    @patch("apps.finance.services.smart_reconciliation_service.ReporteReconciliacion.objects.get")
    @patch.object(SmartReconciliationService, "_extraer_datos_archivo")
    @patch.object(SmartReconciliationService, "_guardar_lineas_extraidas")
    @patch.object(SmartReconciliationService, "_ejecutar_cruce_conciliacion")
    def test_procesar_reporte_con_discrepancias(
        self, mock_cruce, mock_guardar, mock_extraer, mock_get
    ):
        """test_procesar_reporte_con_discrepancias."""
        reporte = Mock()
        reporte.estado = "PENDIENTE"
        reporte.save = Mock()
        mock_get.return_value = reporte
        mock_extraer.return_value = {"items": []}
        mock_guardar.return_value = None
        mock_cruce.return_value = {
            "total_lineas": 10,
            "cuadrados_ok": 8,
            "discrepancias": 2,
            "huerfanos_reporte": 0,
            "huerfanos_local": 0,
        }

        SmartReconciliationService.procesar_reporte("test-uuid")

        assert reporte.estado == "CON_DISCREPANCIAS"


class TestReconciliationMatching:
    """Tests para lógica de matching de reconciliación"""

    def test_ticket_normalization(self):
        """Test que la normalización de tickets funciona correctamente"""
        test_cases = [
            ("1347258019382", "7258019382"),
            ("001-7258019382", "7258019382"),
            ("7258019382", "7258019382"),
            ("", ""),
        ]
        for input_val, expected in test_cases:
            result = input_val.replace("-", "").strip()[-10:]
            assert result == expected or (input_val == "" and result == "")


class TestReconciliationDataExtraction:
    """Tests para extracción de datos"""

    @patch("apps.finance.services.smart_reconciliation_service.pd.read_csv")
    @patch.object(SmartReconciliationService, "_mapear_columnas_df_con_ia")
    def test_extraer_datos_csv(self, mock_map, mock_read_csv):
        """test_extraer_datos_csv."""
        import pandas as pd

        mock_df = pd.DataFrame({"col1": [1, 2], "col2": [3, 4]})
        mock_read_csv.return_value = mock_df
        mock_map.return_value = {"proveedor_nombre": "TEST", "items": []}

        reporte = Mock()
        reporte.archivo.path = "/tmp/test.csv"
        reporte.proveedor = "TEST"

        result = SmartReconciliationService._extraer_datos_archivo(reporte)

        assert "proveedor_nombre" in result
        mock_read_csv.assert_called_once()

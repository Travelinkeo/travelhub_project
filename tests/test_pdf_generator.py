"""Tests para Pdf generator."""
from unittest.mock import patch

import pytest

from apps.automation.parsers.pdf_generation import PdfGenerationService, generate_ticket_pdf


@pytest.fixture
def sample_ticket_data():
    """Sample ticket data."""
    return {
        "SOURCE_SYSTEM": "KIU",
        "NOMBRE_DEL_PASAJERO": "DUQUE ECHEVERRY/OSCA FLORIDA",
        "NUMERO_DE_BOLETO": "0190000000000",
        "FECHA_DE_EMISION": "18 AUG 2023",
        "CODIGO_RESERVA": "ABC123",
        "NOMBRE_AEROLINEA": "SATENA S.A",
        "TARIFA_IMPORTE": "100.00",
        "TOTAL": "110.00",
        "moneda": "USD",
        "segmentos": [
            {
                "aerolinea": "9R",
                "vuelo": "8901",
                "origen": "CCS",
                "destino": "BOG",
                "fecha_salida": "2023-08-25",
                "hora_salida": "09:45",
                "fecha_llegada": "2023-08-25",
                "hora_llegada": "10:46",
                "clase": "Y",
                "localizador_aerolinea": "XYZ789",
            }
        ],
    }


@pytest.fixture
def mock_pdf_renderer():
    """Mock pdf renderer."""
    with patch("apps.automation.parsers.pdf_generation.PdfRendererService") as mock_renderer:
        mock_renderer.check_health.return_value = True
        mock_renderer.render_html_to_pdf.return_value = b"%PDF-1.4 dummy contents"
        yield mock_renderer


@pytest.mark.django_db
def test_generate_ticket_success(sample_ticket_data, mock_pdf_renderer):
    """Generate ticket success."""
    pdf_bytes, filename = PdfGenerationService.generate_ticket(sample_ticket_data)
    assert pdf_bytes == b"%PDF-1.4 dummy contents"
    assert filename.startswith("Boleto_0190000000000_")
    assert filename.endswith(".pdf")
    mock_pdf_renderer.render_html_to_pdf.assert_called_once()


@pytest.mark.django_db
def test_generate_ticket_gotenberg_offline(sample_ticket_data, mock_pdf_renderer):
    """Generate ticket gotenberg offline."""
    mock_pdf_renderer.render_html_to_pdf.side_effect = Exception("Gotenberg offline simulation")
    pdf_bytes, filename = PdfGenerationService.generate_ticket(sample_ticket_data)
    assert pdf_bytes == b""
    assert filename == "error_generacion.pdf"


@pytest.mark.django_db
def test_build_context_passenger_name_parsing(sample_ticket_data):
    # Test typical APELLIDO/NOMBRE split
    """Build context passenger name parsing."""
    context = PdfGenerationService._build_context(
        sample_ticket_data, agencia_obj=None, source_system="KIU"
    )
    assert context["solo_nombre_pasajero"] == "OSCA"
    assert context["NOMBRE_DEL_PASAJERO"] == "DUQUE ECHEVERRY/OSCA"
    assert context["CODIGO_RESERVA"] == "ABC123"
    assert context["TOTAL_MONEDA"] == "USD"
    assert len(context["vuelos"]) == 1


@pytest.mark.django_db
def test_build_context_passenger_name_no_slash():
    """Build context passenger name no slash."""
    data = {"NOMBRE_DEL_PASAJERO": "JUAN PEREZ", "NUMERO_DE_BOLETO": "123"}
    context = PdfGenerationService._build_context(data, agencia_obj=None, source_system="KIU")
    assert context["solo_nombre_pasajero"] == "JUAN"


@pytest.mark.django_db
def test_build_context_agency_obj_fallback(sample_ticket_data):
    # Test that context resolves agency attributes with proxy even if agencia_obj is None
    """Build context agency obj fallback."""
    context = PdfGenerationService._build_context(
        sample_ticket_data, agencia_obj=None, source_system="KIU"
    )
    agency_proxy = context["agencia"]
    assert agency_proxy.nombre == "TRAVELHUB"
    assert agency_proxy.color_primario == "#0D1E40"
    assert agency_proxy.email_principal == "info@travelhub.com"


@pytest.mark.django_db
def test_module_level_function_shortcut(sample_ticket_data, mock_pdf_renderer):
    """Module level function shortcut."""
    pdf_bytes, filename = generate_ticket_pdf(sample_ticket_data)
    assert pdf_bytes == b"%PDF-1.4 dummy contents"
    assert filename.startswith("Boleto_0190000000000_")

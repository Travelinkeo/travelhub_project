from unittest.mock import patch

import pytest

from apps.automation.parsers.pdf_generation import generate_ticket_pdf


@pytest.fixture(autouse=True)
def mock_pdf_renderer():
    with patch("apps.automation.parsers.pdf_generation.PdfRendererService") as mock_renderer:
        mock_renderer.check_health.return_value = True
        mock_renderer.render_html_to_pdf.return_value = b"%PDF-1.4 dummy contents"
        yield mock_renderer


@pytest.mark.django_db
@pytest.mark.parametrize(
    "raw_name,expected",
    [
        ("DUQUE ECHEVERRY/OSCA (CIUDAD DE PANAMA)", "DUQUE ECHEVERRY/OSCA"),
        ("DUQUE ECHEVERRY/OSCA (CIUDAD DE PANAMA) (PANAMA)", "DUQUE ECHEVERRY/OSCA"),
        ("DUQUE ECHEVERRY/OSCA", "DUQUE ECHEVERRY/OSCA"),
    ],
)
def test_pdf_name_sanitization(raw_name, expected):
    data = {
        "SOURCE_SYSTEM": "KIU",
        "SOLO_NOMBRE_PASAJERO": "OSCA",
        "SOLO_CODIGO_RESERVA": "ABC123",
        "NUMERO_DE_BOLETO": "0190000000000",
        "NOMBRE_DEL_PASAJERO": raw_name,
        "CODIGO_IDENTIFICACION": "IDTEST",
        "FECHA_DE_EMISION": "18 AUG 2023 19:12",
        "AGENTE_EMISOR": "AGT123",
        "NOMBRE_AEROLINEA": "SATENA S.A",
        "DIRECCION_AEROLINEA": "AV PRINCIPAL 123",
        "TARIFA": "USD 100.00",
        "IMPUESTOS": "AK 10.00",
        "TOTAL": "USD 110.00",
        "ItinerarioFinalLimpio": "CARACAS 9R8901 25AUG 0945 1046",
    }
    pdf_bytes, filename = generate_ticket_pdf(data)
    # El PDF se genera; verificamos que el nombre saneado no incluya parentesis
    # (Chequeo indirecto: el data mutado en generate_ticket_pdf ya está limpio)
    assert data["NOMBRE_DEL_PASAJERO"] == expected
    # Validación ligera de que se generó algo
    assert isinstance(pdf_bytes, bytes | bytearray) and len(pdf_bytes) > 0

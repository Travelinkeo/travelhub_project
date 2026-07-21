import os

import pytest

from apps.automation.services.ai_parser import parse_ticket_with_gemini

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
SABRE_DIR = os.path.join(PROJECT_ROOT, "external_ticket_generator", "SABRE")
SINGLE_TICKET_FILE = "0457281019415.txt"


def read_ticket(filename: str):
    path = os.path.join(SABRE_DIR, filename)
    with open(path, encoding="utf-8", errors="ignore") as f:
        return f.read()


@pytest.mark.django_db
@pytest.mark.vcr
def test_parse_sabre_ticket_with_gemini():
    try:
        from django.conf import settings

        if not settings.GEMINI_API_KEY:
            pytest.skip("GEMINI_API_KEY no está configurada, saltando prueba de IA.")
    except ImportError:
        pytest.skip("No se pudo importar la configuración de Django.")

    ticket_text = read_ticket(SINGLE_TICKET_FILE)
    parsed_data = parse_ticket_with_gemini(ticket_text)

    assert parsed_data is not None
    assert "normalized" in parsed_data
    normalized = parsed_data["normalized"]
    assert "passenger" in normalized
    assert "bookingDetails" in normalized
    assert "flights" in normalized
    assert isinstance(normalized["flights"], list)

    assert parsed_data.get("SOURCE_SYSTEM") == "GEMINI_AI"
    assert normalized["passenger"].get("name") == "JUAREZ/RAUL"
    assert normalized["bookingDetails"].get("ticketNumber") == "0457281019415"
    assert len(normalized["flights"]) == 1

    flight = normalized["flights"][0]
    assert "CARACAS" in flight["departure"]["location"]
    assert "BOGOTA" in flight["arrival"]["location"]

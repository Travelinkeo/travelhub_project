import os

import pytest

from apps.automation.services.ai_parser import parse_ticket_with_gemini

pytestmark = pytest.mark.skip(reason="Parser/Gemini refactorizado - pendiente actualización")

# --- Helpers para leer datos de prueba ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
SABRE_DIR = os.path.join(PROJECT_ROOT, "external_ticket_generator", "SABRE")
SINGLE_TICKET_FILE = "0457281019415.txt"


def read_ticket(filename: str):
    path = os.path.join(SABRE_DIR, filename)
    with open(path, encoding="utf-8", errors="ignore") as f:
        return f.read()


# --- Pruebas del Parser de IA ---


@pytest.mark.django_db
@pytest.mark.vcr
def test_parse_sabre_ticket_with_gemini():
    """
    Prueba de extremo a extremo que valida el parser de Gemini con un boleto de Sabre.
    Usa pytest-vcr para grabar y reproducir la respuesta de la API, evitando llamadas reales en tests repetidos.
    """
    # Cargar la API Key de Django settings; si no está, el test se saltará.
    # Esto es mejor que fallar si la clave no está en el entorno de CI.
    try:
        from django.conf import settings

        if not settings.GEMINI_API_KEY:
            pytest.skip("GEMINI_API_KEY no está configurada, saltando prueba de IA.")
    except ImportError:
        pytest.skip("No se pudo importar la configuración de Django.")

    # Leer el contenido del boleto de prueba
    ticket_text = read_ticket(SINGLE_TICKET_FILE)

    # Llamar a la función de parseo con IA
    parsed_data = parse_ticket_with_gemini(ticket_text)

    # --- Aserciones de Validación ---

    # 1. Verificar que obtuvimos una respuesta válida
    assert (
        parsed_data is not None
    ), "El parser de IA no debería devolver None con una API key válida."

    # 2. Verificar la estructura principal del JSON
    assert "normalized" in parsed_data
    normalized = parsed_data["normalized"]
    assert "passenger" in normalized
    assert "bookingDetails" in normalized
    assert "flights" in normalized
    assert isinstance(normalized["flights"], list)

    # 3. Verificar metadatos y datos clave
    assert parsed_data.get("SOURCE_SYSTEM") == "GEMINI_AI"
    assert normalized["passenger"].get("name") == "JUAREZ/RAUL"
    assert normalized["bookingDetails"].get("ticketNumber") == "0457281019415"
    assert len(normalized["flights"]) == 1

    # 4. Verificar datos específicos del vuelo
    flight = normalized["flights"][0]
    assert flight.get("flightNumber") == "AA123" or flight.get("flightNumber") == "123"
    assert "CARACAS" in flight["departure"]["location"]
    assert "BOGOTA" in flight["arrival"]["location"]

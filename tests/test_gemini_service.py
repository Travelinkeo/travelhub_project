# tests/test_gemini_service.py
import os

import pytest

from apps.automation.services.ai_engine import generate_text_from_prompt

# Marcador de Pytest para omitir este test si la API key no está disponible.
# Esto es útil para entornos de CI/CD donde no se configuran secretos.
requires_gemini_api = pytest.mark.skipif(
    not os.getenv("GEMINI_API_KEY") or "placeholder" in os.getenv("GEMINI_API_KEY", "").lower(),
    reason="Se requiere GEMINI_API_KEY real para este test de integración.",
)


@requires_gemini_api
def test_gemini_api_connectivity(monkeypatch):
    """
    Test de integración real: Verifica la conectividad con la API de Gemini.

    Este test envía un prompt simple y comprueba que recibe una respuesta
    coherente y sin errores. Confirma que la API Key es válida y la
    configuración del cliente es correcta.
    """
    # 1. Arrange: Restaurar el call_gemini original para evitar el mock de conftest.py
    from apps.automation.services.ai_engine import AIEngine, ai_engine

    monkeypatch.setattr(ai_engine, "call_gemini", AIEngine.call_gemini.__get__(ai_engine, AIEngine))

    prompt = "Hola. Responde solo con la palabra: 'ok'"

    # 2. Act
    response = generate_text_from_prompt(prompt)

    # 3. Assert
    assert isinstance(response, str)
    assert len(response) > 0
    assert "Error" not in response
    # Verificamos que la respuesta sea más o menos lo que esperamos
    assert "ok" in response.lower()

    print(f"Respuesta de la API de Gemini: {response}")

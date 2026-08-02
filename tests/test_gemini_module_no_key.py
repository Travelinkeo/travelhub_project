import pytest

from apps.automation.services import ai_engine


def test_gemini_without_api_key(monkeypatch):
    """test_gemini_without_api_key."""
    # Sin API key configurada, AIEngine no debe estar listo ni lanzar llamadas reales.
    monkeypatch.setattr(
        "apps.automation.services.ai_engine.get_gemini_api_key", lambda *a, **k: None
    )
    monkeypatch.setattr("apps.automation.services.ai_engine.ai_engine.is_ready", False)
    assert ai_engine.ai_engine.is_ready is False


def test_generate_content_raises_gemini_configuration_error(monkeypatch):
    """test_generate_content_raises_gemini_configuration_error."""
    from apps.automation.providerchain.fallback_router import fallback_router

    def fake_generate(**kwargs):
        raise ai_engine.GeminiConfigurationError("No hay API key configurada")

    monkeypatch.setattr(fallback_router, "generate", fake_generate)

    with pytest.raises(ai_engine.GeminiConfigurationError):
        ai_engine.analizar_documento_con_gemini_estructurado(
            b"fake", "application/pdf", "test", dict
        )

import pytest
pytestmark = pytest.mark.skip(reason='Parser/Gemini refactorizado - pendiente actualización')
import importlib
import sys



def test_gemini_without_api_key(settings, monkeypatch):
    if hasattr(settings, 'GEMINI_API_KEY'):
        delattr(settings, 'GEMINI_API_KEY')

    if 'apps.automation.services.ai_engine' in sys.modules:
        del sys.modules['apps.automation.services.ai_engine']

    ai_engine = importlib.import_module('apps.automation.services.ai_engine')

    with pytest.raises(ai_engine.GeminiConfigurationError):
        ai_engine.analizar_documento_con_gemini_estructurado(
            b"fake", "application/pdf", "test", dict
        )

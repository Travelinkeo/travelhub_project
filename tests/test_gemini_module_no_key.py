import importlib
import sys

import pytest


def test_gemini_without_api_key(settings, monkeypatch):
    # Asegurar que no exista la clave en settings
    if hasattr(settings, 'GEMINI_API_KEY'):
        delattr(settings, 'GEMINI_API_KEY')

    # Forzar recarga limpia del módulo core.gemini
    if 'core.gemini' in sys.modules:
        del sys.modules['core.gemini']

    gemini = importlib.import_module('core.gemini')

    with pytest.raises(gemini.GeminiConfigurationError):
        gemini.get_gemini_model()

    with pytest.raises(gemini.GeminiConfigurationError):
        gemini.generate_content('hola')

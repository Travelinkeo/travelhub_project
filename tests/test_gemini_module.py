import unittest
from unittest.mock import patch

from django.test import override_settings

from apps.automation.services.ai_engine import GeminiConfigurationError


class TestGeminiModule(unittest.TestCase):

    @override_settings(GEMINI_API_KEY=None)
    @patch("os.getenv")
    def test_gemini_configuration_error_if_key_is_missing(self, mock_getenv):
        mock_getenv.return_value = None

        with self.assertRaises(GeminiConfigurationError) as cm:
            from apps.automation.services.ai_engine import (
                analizar_documento_con_gemini_estructurado,
            )
            analizar_documento_con_gemini_estructurado(b"fake", "application/pdf", "test", dict)

        self.assertIn("GEMINI_API_KEY", str(cm.exception))

    @override_settings(GEMINI_API_KEY="fake-api-key")
    def test_gemini_succeeds_if_key_exists(self):
        import importlib

        from apps.automation.services import ai_engine as mod
        importlib.reload(mod)

        try:
            self.assertTrue(mod.ai_engine is not None)
        except GeminiConfigurationError:
            self.fail("ai_engine levanto GeminiConfigurationError inesperadamente.")

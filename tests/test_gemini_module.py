"""Tests para Gemini module."""
import unittest
from unittest.mock import patch

from apps.automation.services.ai_engine import GeminiConfigurationError


class TestGeminiModule(unittest.TestCase):
    @patch("apps.automation.services.ai_engine.get_gemini_api_key", return_value=None)
    """Test Gemini Module."""
    def test_gemini_configuration_error_if_key_is_missing(self, mock_get_key):
        """Gemini configuration error if key is missing."""
        from apps.automation.services.ai_engine import (
            analizar_documento_con_gemini_estructurado,
        )

        with self.assertRaises(GeminiConfigurationError) as cm:
            analizar_documento_con_gemini_estructurado(b"fake", "application/pdf", "test", dict)

        self.assertIn("GEMINI_API_KEY", str(cm.exception))

    @patch("apps.automation.services.ai_engine.get_gemini_api_key", return_value="fake-api-key")
    @patch("apps.automation.services.ai_engine._get_genai")
    def test_gemini_succeeds_if_key_exists(self, mock_get_genai, mock_get_key):
        """Gemini succeeds if key exists."""
        from apps.automation.services.ai_engine import ai_engine

        # Reset clients cache to ensure client creation is triggered
        ai_engine._clients_cache = {}

        try:
            client = ai_engine._get_client()
            self.assertIsNotNone(client)
        except GeminiConfigurationError:
            self.fail("ai_engine levantó GeminiConfigurationError inesperadamente.")

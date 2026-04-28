import unittest
from unittest.mock import patch

from django.test import override_settings

# Importar el módulo y la excepción específica
from core.gemini import GeminiConfigurationError


class TestGeminiModule(unittest.TestCase):

    @override_settings(GEMINI_API_KEY=None)
    def test_get_gemini_model_raises_error_if_key_is_missing(self):
        """
        Verifica que se lanza GeminiConfigurationError si la GEMINI_API_KEY no está configurada.
        """
        # Forzar la recarga del módulo de gemini bajo la configuración modificada
        # para que la comprobación a nivel de módulo se re-evalue.
        import importlib

        from core import gemini
        importlib.reload(gemini)

        with self.assertRaises(GeminiConfigurationError) as cm:
            gemini.get_gemini_model()
        
        self.assertEqual(
            str(cm.exception),
            "GEMINI_API_KEY no configurada en settings.",
            "El mensaje de la excepción no es el esperado."
        )

    @override_settings(GEMINI_API_KEY="fake-api-key")
    def test_get_gemini_model_succeeds_if_key_exists(self):
        """
        Verifica que no se lanza ninguna excepción si la GEMINI_API_KEY sí existe.
        Esto es un caso de prueba positivo para asegurar que no rompemos la funcionalidad normal.
        """
        # Recargar el módulo para que _GEMINI_READY se establezca a True
        import importlib

        from core import gemini
        importlib.reload(gemini)
        
        try:
            # Usamos un mock para evitar la llamada real a la API de Google
            with patch('google.generativeai.GenerativeModel') as mock_generative_model:
                gemini.get_gemini_model()
                mock_generative_model.assert_called_once_with('gemini-pro')
        except GeminiConfigurationError:
            self.fail("get_gemini_model() lanzó GeminiConfigurationError inesperadamente.")
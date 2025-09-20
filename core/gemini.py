import google.generativeai as genai
from django.conf import settings

class GeminiConfigurationError(RuntimeError):
    """Se lanza cuando la clave de API de Gemini no está configurada."""

API_KEY = getattr(settings, 'GEMINI_API_KEY', None)
if not API_KEY:
    _GEMINI_READY = False
else:
    genai.configure(api_key=API_KEY)
    _GEMINI_READY = True

def get_gemini_model(force_json_output: bool = False):
    """
    Inicializa y retorna un modelo generativo de Gemini.

    :param force_json_output: Si es True, configura el modelo para forzar una salida JSON.
    :return: Una instancia del modelo generativo.
    :raises GeminiConfigurationError: si la API key no está configurada.
    """
    if not _GEMINI_READY:
        raise GeminiConfigurationError("GEMINI_API_KEY no configurada en settings.")

    if force_json_output:
        # Usa un modelo más nuevo que soporte la salida JSON forzada.
        model_name = "gemini-1.5-pro-latest"
        generation_config = {
            "temperature": 0.1,
            "max_output_tokens": 8192,
            "response_mime_type": "application/json",
        }
        return genai.GenerativeModel(
            model_name=model_name,
            generation_config=generation_config
        )
    else:
        # Comportamiento por defecto para mantener compatibilidad
        return genai.GenerativeModel('gemini-pro')

def generate_content(prompt: str) -> str:
    """Genera contenido usando el modelo Gemini.

    :param prompt: Texto de entrada.
    :return: Respuesta de texto del modelo.
    :raises GeminiConfigurationError: si la API key no está configurada.
    """
    # Llama a la función base sin forzar JSON para mantener el comportamiento original
    model = get_gemini_model(force_json_output=False)
    response = model.generate_content(prompt)
    return getattr(response, 'text', '')
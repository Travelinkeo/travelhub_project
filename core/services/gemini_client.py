# core/services/gemini_client.py
# MIGRADO a SDK google-genai (v1.x) — librería oficial de Google.
# La librería anterior (google.generativeai) está deprecada.
import logging
import os
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

if not GEMINI_API_KEY:
    logger.warning("GEMINI_API_KEY no encontrada en las variables de entorno. El cliente de Gemini no funcionará.")

# ─────────────────────────────────────────────────────────────
# Helpers Internos
# ─────────────────────────────────────────────────────────────

def _get_client() -> genai.Client | None:
    """Devuelve un cliente Gemini autenticado o None si falta la clave."""
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        logger.error("No se puede usar Gemini sin una API Key.")
        return None
    return genai.Client(api_key=api_key)


# ─────────────────────────────────────────────────────────────
# API Pública (mantiene compatibilidad con el código existente)
# ─────────────────────────────────────────────────────────────

def get_gemini_model(model_name: str = "gemini-2.0-flash-lite-001"):
    """
    Mantiene compatibilidad con código que llame a get_gemini_model().
    Ahora devuelve el cliente directamente — cada llamada usa client.models.generate_content().
    """
    return _get_client()


def list_available_models():
    """Lista los modelos disponibles en la cuenta."""
    c = _get_client()
    if not c:
        return "Error: No se proporcionó API Key."
    try:
        models = [m.name for m in c.models.list()]
        return models
    except Exception as e:
        logger.error(f"Error al listar modelos de Gemini: {e}", exc_info=True)
        return f"Error al contactar la API de Gemini: {e}"


def generate_text_from_prompt(prompt: str, model_name: str = "gemini-2.0-flash-lite-001") -> str:
    """Envía un prompt de texto a Gemini y devuelve la respuesta."""
    c = _get_client()
    if not c:
        return "Error: El cliente de Gemini no pudo ser inicializado."
    try:
        response = c.models.generate_content(
            model=model_name,
            contents=prompt
        )
        return response.text
    except Exception as e:
        logger.error(f"Error en generate_text_from_prompt: {e}", exc_info=True)
        return f"Error al contactar la API de Gemini: {e}"


def generate_structured_data(prompt: str, model_name: str = "gemini-2.0-flash-lite-001") -> str:
    """Envía un prompt a Gemini y fuerza respuesta en formato JSON."""
    c = _get_client()
    if not c:
        return "{}"
    try:
        response = c.models.generate_content(
            model=model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )
        return response.text
    except Exception as e:
        logger.error(f"Error en generate_structured_data: {e}", exc_info=True)
        return "{}"

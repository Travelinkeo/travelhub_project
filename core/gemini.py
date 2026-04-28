# core/gemini.py
# MIGRADO a SDK google-genai (v1.x) — librería oficial de Google.
# La librería anterior (google.generativeai) está deprecada y fue eliminada.
import os
import json
from typing import Type
from django.conf import settings
from google import genai
from google.genai import types


class GeminiConfigurationError(RuntimeError):
    """Se lanza cuando la clave de API de Gemini no está configurada."""


def _get_api_key() -> str | None:
    return getattr(settings, 'GEMINI_API_KEY', None) or os.getenv('GEMINI_API_KEY')


def _get_client() -> genai.Client:
    """Devuelve un cliente Gemini autenticado o lanza GeminiConfigurationError."""
    api_key = _get_api_key()
    if not api_key:
        raise GeminiConfigurationError("GEMINI_API_KEY no configurada en settings.")
    return genai.Client(api_key=api_key)


def get_gemini_model(force_json_output: bool = False):
    """
    Mantiene compatibilidad con código que llame a get_gemini_model().
    Ahora devuelve el cliente genai directamente.
    El parámetro force_json_output se respeta internamente en generate_content/analizar_documento.
    """
    return _get_client()


def generate_content(prompt: str, model_name: str = "gemini-2.0-flash") -> str:
    """
    Genera contenido de texto usando Gemini.

    :param prompt: Texto de entrada.
    :param model_name: Modelo a utilizar.
    :return: Respuesta de texto del modelo.
    :raises GeminiConfigurationError: si la API key no está configurada.
    """
    c = _get_client()
    response = c.models.generate_content(
        model=model_name,
        contents=prompt
    )
    return getattr(response, 'text', '')


def analizar_documento_con_gemini_estructurado(
    file_bytes: bytes,
    mime_type: str,
    prompt_text: str,
    response_schema: Type
) -> dict:
    """
    Sube un documento inline a Gemini y retorna un dict basado en un modelo Pydantic/schema.

    :param file_bytes: Contenido binario del archivo (PDF, imagen, etc.)
    :param mime_type: MIME type del archivo (ej. "application/pdf", "image/jpeg")
    :param prompt_text: Instrucción para el modelo.
    :param response_schema: Esquema Pydantic que define la estructura del JSON esperado.
    :return: Diccionario parseado con los datos extraídos.
    :raises GeminiConfigurationError: si la API key no está configurada.
    :raises ValueError: si Gemini no devuelve JSON válido.
    """
    c = _get_client()

    response = c.models.generate_content(
        model="gemini-2.0-flash",
        contents=[
            types.Part.from_bytes(data=file_bytes, mime_type=mime_type),
            prompt_text
        ],
        config=types.GenerateContentConfig(
            temperature=0.1,
            response_mime_type="application/json",
            response_schema=response_schema,
        )
    )

    try:
        data = json.loads(response.text)
        return data
    except Exception as e:
        raise ValueError(
            f"Gemini no devolvió un JSON válido para el esquema. Respuesta: {response.text}"
        ) from e
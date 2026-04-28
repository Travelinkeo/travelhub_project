import os
import requests
import tempfile
import logging
import json
from django.conf import settings
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

TWILIO_SID = getattr(settings, 'TWILIO_ACCOUNT_SID', None)
TWILIO_AUTH = getattr(settings, 'TWILIO_AUTH_TOKEN', None)


def _get_client() -> genai.Client | None:
    api_key = getattr(settings, 'GEMINI_API_KEY', None) or os.getenv('GEMINI_API_KEY')
    if not api_key:
        logger.error("GEMINI_API_KEY no configurada.")
        return None
    return genai.Client(api_key=api_key)


def download_twilio_media(media_url: str) -> str:
    """
    Descarga el archivo de audio multimedia desde Twilio hacia un archivo temporal.
    """
    try:
        logger.info(f"Descargando audio de Twilio: {media_url}")

        auth = None
        if TWILIO_SID and TWILIO_AUTH and 'twilio.com' in media_url.lower():
            auth = (TWILIO_SID, TWILIO_AUTH)

        headers = {'User-Agent': 'Mozilla/5.0 TravelHub-Voice-Bot'}
        response = requests.get(media_url, auth=auth, headers=headers, stream=True, timeout=15)
        response.raise_for_status()

        content_type = response.headers.get('Content-Type', '')
        ext = '.ogg'
        if 'mp4' in content_type: ext = '.mp4'
        elif 'mp3' in content_type: ext = '.mp3'
        elif 'amr' in content_type: ext = '.amr'

        fd, temp_path = tempfile.mkstemp(suffix=ext)
        with os.fdopen(fd, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk: f.write(chunk)

        return temp_path

    except Exception as e:
        logger.error(f"Error descargando media de Twilio: {e}")
        return None


def extract_quote_intent_from_audio(file_path: str) -> dict:
    """
    Sube el archivo local de audio a Gemini y extrae parámetros de cotización en JSON.
    MIGRADO a SDK google-genai (v1.x) — usa Files API y generate_content inline.
    """
    client = _get_client()
    if not client:
        return {"error": "Gemini no configurado"}

    logger.info(f"Procesando audio por Gemini: {file_path}")
    uploaded_file = None

    json_prompt = """
    Eres un Agente de Viajes IA súper experto.
    Escucha cuidadosamente la siguiente nota de voz o lee el mensaje del prospecto.
    Su intención es pedir una cotización o presupuesto de viaje.

    Devuelve un JSON estrictamente estructurado (sin backticks):
    {
      "destino": "Ciudad o país del destino mencionado (String)",
      "origen": "Ciudad de origen si la menciona (String)",
      "numero_pasajeros": "Número de personas que viajan (Entero). Mínimo 1.",
      "mes_viaje": "Mes aproximado o fecha mencionada (String)",
      "intencion": "Resumen directo en 1 oración de lo que quiere (String)",
      "tipo": "VUELO, ALOJAMIENTO, PAQUETE, SEGURO o VARIOS (String)",
      "transcripcion": "Transcripción más fiel posible del audio (String)"
    }
    """

    try:
        # Subir archivo de audio usando Files API del nuevo SDK
        with open(file_path, 'rb') as f:
            audio_bytes = f.read()

        # Inferir mime desde extensión
        mime = 'audio/ogg'
        if file_path.endswith('.mp3'): mime = 'audio/mp3'
        elif file_path.endswith('.mp4'): mime = 'audio/mp4'
        elif file_path.endswith('.amr'): mime = 'audio/amr'

        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=[
                types.Part.from_bytes(data=audio_bytes, mime_type=mime),
                json_prompt
            ],
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )

        text_resp = response.text.strip()
        if text_resp.startswith("```json"): text_resp = text_resp[7:]
        if text_resp.endswith("```"): text_resp = text_resp[:-3]

        data = json.loads(text_resp)
        logger.info(f"Intención de cotización extraída: {data.get('destino')}")
        return data

    except Exception as e:
        logger.error(f"Error procesando audio con Gemini: {e}")
        return {"error": str(e), "transcripcion": f"Fallo al transcribir audio: {str(e)}"}

    finally:
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as e:
                logger.debug(f"Error eliminando archivo local temporal: {e}")


def process_twilio_audio_message(media_url: str) -> dict:
    """Orquestador: Descarga de Twilio → Extrae IA → Borra archivo tmp."""
    local_path = download_twilio_media(media_url)
    if not local_path:
        return {"error": "Fallo descarga del audio."}
    return extract_quote_intent_from_audio(local_path)


def process_twilio_text_message(text_body: str) -> dict:
    """Procesador alternativo cuando es sólo texto."""
    client = _get_client()
    if not client:
        return {"error": "Gemini no preparado"}

    json_prompt = f"""
    Eres un Agente de Viajes IA experto en procesar chats de WhatsApp.
    Analiza esta solicitud de cotización y devuelve SOLO el siguiente JSON (sin backticks):
    {{
      "destino": "Ciudad/País (String)",
      "origen": "Ciudad origen (String)",
      "numero_pasajeros": "Inferido (Integer). Mínimo 1.",
      "mes_viaje": "Mes/Fecha (String)",
      "intencion": "Resumen en una frase (String)",
      "tipo": "VUELO, ALOJAMIENTO, PAQUETE o VARIOS (String)",
      "transcripcion": "El mensaje original completo (String)"
    }}
    Mensaje del cliente: "{text_body}"
    """
    try:
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=json_prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )
        text_resp = response.text.strip()
        if text_resp.startswith("```json"): text_resp = text_resp[7:]
        if text_resp.endswith("```"): text_resp = text_resp[:-3]
        return json.loads(text_resp)
    except Exception as e:
        logger.error(f"Error NLP Texto: {e}")
        return {"error": str(e)}

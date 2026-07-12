import json
import logging

logger = logging.getLogger(__name__)


def _get_genai():
    from google import genai

    return genai


class AudioTranscriptionService:
    """
    Servicio para transcribir audios y extraer datos estructurados
    utilizando Google Gemini (Multimodal).
    """

    def __init__(self, agency=None):
        from apps.automation.services.ai_engine import get_gemini_api_key

        self.api_key = get_gemini_api_key(agency)
        if not self.api_key:
            logger.error("GEMINI_API_KEY no configurada.")
            self.client = None
            return

        try:
            genai = _get_genai()
            self.client = genai.Client(api_key=self.api_key)
            self.model_name = "gemini-1.5-flash"
        except Exception as e:
            logger.error(f"Error configurando Gemini AI: {e}")
            self.client = None

    def transcribe_and_extract(self, audio_file_path):
        """
        Sube el audio a Gemini, lo transcribe y extrae datos de viaje.

        Args:
            audio_file_path (str): Ruta local al archivo de audio (ogg, mp3, wav).

        Returns:
            dict: {
                "transcription": "Texto completo...",
                "structure": { ...JSON con datos... },
                "error": None
            }
        """
        if not self.client:
            return {"error": "API Key no configurada"}

        try:
            logger.info(f"Subiendo audio a Gemini: {audio_file_path}")

            audio_file = self.client.files.upload(path=audio_file_path)

            prompt = """
            Actúa como un agente de viajes experto. Tu tarea es escuchar este audio del cliente y hacer dos cosas:
            1. Transcribir exactamente lo que dice el cliente.
            2. Extraer los datos clave del viaje en formato JSON.

            Si el audio no es sobre viajes, simplemente transcribe y deja el JSON vacío.

            Devuelve tu respuesta EXACTAMENTE en este formato JSON (sin markdown):
            {
                "transcription": "Aquí va la transcripción del audio...",
                "travel_data": {
                    "origin": "CIUDAD (Código IATA si es posible)",
                    "destination": "CIUDAD (Código IATA si es posible)",
                    "departure_date": "YYYY-MM-DD (Estima el año si dicen 'el 15 de enero')",
                    "return_date": "YYYY-MM-DD o null si es solo ida",
                    "passengers": "Número de pasajeros o descripción",
                    "notes": "Cualquier otro detalle (preferencia de aerolínea, horario, etc)"
                }
            }
            """

            logger.info("Enviando prompt a Gemini...")
            response = self.client.models.generate_content(
                model=self.model_name, contents=[prompt, audio_file]
            )

            response_text = response.text

            clean_text = response_text.replace("```json", "").replace("```", "").strip()

            try:
                result = json.loads(clean_text)
                return result
            except json.JSONDecodeError:
                logger.error(f"Error decodificando JSON de Gemini: {response_text}")
                return {
                    "transcription": response_text,
                    "travel_data": None,
                    "error": "Error de formato JSON",
                }

        except Exception as e:
            logger.error(f"Error procesando audio con Gemini: {e}")
            return {"error": str(e)}

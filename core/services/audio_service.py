
import logging
import os
import json
import google.generativeai as genai
from django.conf import settings

logger = logging.getLogger(__name__)

class AudioTranscriptionService:
    """
    Servicio para transcribir audios y extraer datos estructurados
    utilizando Google Gemini (Multimodal).
    """

    def __init__(self):
        self.api_key = getattr(settings, 'GEMINI_API_KEY', None)
        if not self.api_key:
            logger.error("GEMINI_API_KEY no configurada en settings.")
            return

        try:
            genai.configure(api_key=self.api_key)
            # Usamos gemini-flash-latest (Alias estable para la versión Flash actual)
            self.model = genai.GenerativeModel('gemini-flash-latest')
        except Exception as e:
            logger.error(f"Error configurando Gemini AI: {e}")

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
        if not self.api_key:
            return {"error": "API Key no configurada"}

        try:
            logger.info(f"Subiendo audio a Gemini: {audio_file_path}")
            
            # 1. Subir archivo a la API de File de Gemini
            # Nota: Esto es diferente a enviar la imagen en bytes. Audio requiere File API.
            audio_file = genai.upload_file(path=audio_file_path)
            
            # 2. Preparar el Prompt
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
            response = self.model.generate_content([prompt, audio_file])
            
            # 3. Procesar respuesta
            response_text = response.text
            
            # Limpiar bloques de código si Gemini los agrega (```json ... ```)
            clean_text = response_text.replace('```json', '').replace('```', '').strip()
            
            try:
                result = json.loads(clean_text)
                return result
            except json.JSONDecodeError:
                logger.error(f"Error decodificando JSON de Gemini: {response_text}")
                # Fallback: devolver al menos el texto crudo
                return {
                    "transcription": response_text,
                    "travel_data": None,
                    "error": "Error de formato JSON"
                }

        except Exception as e:
            logger.error(f"Error procesando audio con Gemini: {e}")
            return {"error": str(e)}

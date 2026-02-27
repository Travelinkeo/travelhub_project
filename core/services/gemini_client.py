# core/services/gemini_client.py
import logging
import os

import google.generativeai as genai

logger = logging.getLogger(__name__)

# --- Configuración del Cliente de Gemini ---

# Se recomienda cargar la clave desde las settings de Django o directamente de las variables de entorno
# para mantener la consistencia con el resto del proyecto.
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

if not GEMINI_API_KEY:
    logger.warning("GEMINI_API_KEY no encontrada en las variables de entorno. El cliente de Gemini no funcionará.")
    # Levantar un error podría ser mejor en producción si la funcionalidad es crítica.
    # raise ValueError("GEMINI_API_KEY is required.")
else:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        logger.info("Cliente de Gemini API configurado exitosamente.")
    except Exception as e:
        logger.error(f"Error al configurar el cliente de Gemini API: {e}", exc_info=True)


def list_available_models():
    """
    Lista los modelos generativos disponibles a través de la API de Gemini
    que soportan la generación de contenido.
    """
    if not GEMINI_API_KEY:
        logger.error("No se puede listar modelos de Gemini sin una API Key.")
        return "Error: No se proporcionó API Key."
    
    try:
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        return models
    except Exception as e:
        logger.error(f"Error al listar los modelos de Gemini: {e}", exc_info=True)
        return f"Error al contactar la API de Gemini para listar modelos: {e}"


def get_gemini_model(model_name: str = "gemini-2.0-flash-lite-001"):
    """
    Inicializa y devuelve un modelo generativo de Gemini.
    """
    if not GEMINI_API_KEY:
        logger.error("No se puede inicializar el modelo de Gemini sin una API Key.")
        return None
    
    try:
        model = genai.GenerativeModel(model_name)
        return model
    except Exception as e:
        logger.error(f"Error al inicializar el modelo '{model_name}': {e}", exc_info=True)
        return None

def generate_text_from_prompt(prompt: str, model_name: str = "gemini-2.0-flash-lite-001") -> str:
    """
    Envía un prompt de texto simple a Gemini y devuelve la respuesta generada.
    """
    model = get_gemini_model(model_name)
    if not model:
        return "Error: El modelo de Gemini no pudo ser inicializado."

    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        logger.error(f"Error durante la generación de contenido con Gemini: {e}", exc_info=True)
        return f"Error al contactar la API de Gemini: {e}"


def generate_structured_data(prompt: str, model_name: str = "gemini-2.0-flash-lite-001") -> str:
    """
    Envía un prompt a Gemini y fuerza una respuesta en formato JSON.
    """
    model = get_gemini_model(model_name)
    if not model:
        return "{}"

    try:
        # Configurar para recibir JSON
        config = genai.types.GenerationConfig(
            response_mime_type="application/json"
        )
        
        response = model.generate_content(prompt, generation_config=config)
        return response.text
    except Exception as e:
        logger.error(f"Error durante la generación de datos estructurados: {e}", exc_info=True)
        return "{}"

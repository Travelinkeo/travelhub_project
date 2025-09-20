
import json
import logging
import re
from typing import Any

from core.gemini import GeminiConfigurationError, generate_content

logger = logging.getLogger(__name__)

# Basado en el ejemplo JSON validado y la estructura deseada.
JSON_SCHEMA_PROMPT = """
{
  "documentTitle": "string",
  "issuingAgent": {
    "name": "string",
    "address": "string",
    "phone": "string",
    "iataNumber": "string"
  },
  "passenger": {
    "name": "string",
    "customerNumber": "string"
  },
  "bookingDetails": {
    "reservationCode": "string",
    "issueDate": "string (YYYY-MM-DD)",
    "ticketNumber": "string",
    "issuingAirline": "string"
  },
  "flights": [
    {
      "date": "string (YYYY-MM-DD)",
      "airline": "string",
      "flightNumber": "string",
      "operatedBy": "string",
      "departure": {
        "location": "string",
        "time": "string (HH:MM)",
        "terminal": "string"
      },
      "arrival": {
        "location": "string",
        "time": "string (HH:MM)",
        "terminal": "string"
      },
      "details": {
        "cabin": "string",
        "baggageAllowance": "string",
        "status": "string",
        "fareBasis": "string"
      }
    }
  ]
}
"""

def parse_ticket_with_gemini(ticket_text: str) -> dict[str, Any] | None:
    """
    Intenta parsear el texto de un boleto de avión usando la API de Gemini.

    :param ticket_text: El contenido en texto plano del boleto.
    :return: Un diccionario con los datos extraídos o None si falla.
    """
    prompt = f"""
    Eres un asistente experto en la industria de viajes. Analiza el siguiente texto de un
    recibo de boleto electrónico y extrae la información clave.

    Devuelve la información SOLAMENTE en formato JSON, adhiriéndote estrictamente al
    siguiente esquema. No incluyas explicaciones, solo el objeto JSON.

    Esquema JSON esperado:
    {JSON_SCHEMA_PROMPT}

    Texto del boleto a analizar:
    ---
    {ticket_text}
    ---
    """

    try:
        logger.info("Iniciando parseo de boleto con Gemini...")
        raw_response = generate_content(prompt)

        # Limpiar la respuesta para asegurar que solo contenga el JSON
        # Busca un bloque que empiece con { y termine con }
        json_match = re.search(r'\{{.*\}}', raw_response, re.DOTALL)
        if not json_match:
            logger.error("Gemini no devolvió un objeto JSON válido en la respuesta.")
            return None
        
        json_string = json_match.group(0)
        parsed_data = json.loads(json_string)
        logger.info("Parseo con Gemini exitoso.")
        
        # Envolver la respuesta en la estructura que el servicio espera
        return {
            'normalized': parsed_data,
            'raw_data': {},
            'SOURCE_SYSTEM': 'GEMINI_AI'
        }

    except GeminiConfigurationError as e:
        logger.error(f"Error de configuración de Gemini: {e}")
        return None
    except json.JSONDecodeError:
        logger.error("Error al decodificar la respuesta JSON de Gemini. Respuesta recibida: {raw_response}")
        return None
    except Exception:
        logger.error("Ocurrió un error inesperado durante el parseo con Gemini: {e}")
        return None

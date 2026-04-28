import json
import logging
import re
from typing import Any

from core.gemini import generate_content

logger = logging.getLogger(__name__)

JSON_STRUCTURE_PROMPT = """
[
  {
    "fecha": "string (DD/MM/YYYY)",
    "nombre_pasajero": "string",
    "numero_boleto": "string",
    "aerolinea_nombre": "string",
    "aerolinea_codigo": "string",
    "tarifa_fare": "float",
    "tax": "float",
    "exchange_canje": "float or null",
    "void": "float or null",
    "sub_total": "float",
    "fee_servicio": "float",
    "comision_porcentaje": "string",
    "comision_venta_tarifa_fare": "float",
    "monto_a_pagar": "float"
  }
]"""

def parse_travelinkeo_report_with_gemini(ocr_text: str) -> list[dict[str, Any]] | None:
    """
    Parsea el texto OCR de un reporte de Travelinkeo usando la API de Gemini.

    Args:
        ocr_text: El texto completo obtenido del PDF del reporte.

    Returns:
        Una lista de diccionarios con los datos de las ventas, o None si falla.
    """
    prompt = f"""
    Por favor, analiza el siguiente texto extraído de un reporte de ventas en PDF.
    El texto contiene datos de ventas de boletos aéreos en un formato tabular.
    Extrae todas las filas de datos de ventas y devuélvelas en un formato JSON válido.
    La respuesta debe ser una lista de objetos JSON, donde cada objeto representa una fila.
    
    Asegúrate de seguir exactamente la estructura y los tipos de datos del siguiente esquema.
    Las columnas son: Fecha, Kiu, Inter, AGENCIA DE VIAJES, Nombre del Pasajero, Nº de Boleto, Aerolinea, Tarifa Fare, TAX, Exchange (canje), Void, Sub-Total, Fee de Servicio, %, Comisión por Venta Tarifa Fare, Monto a pagar.
    Si un valor numérico no está presente, usa null.
    Limpia los nombres de pasajero, eliminando texto como "(GOMEZ RAMIREZ, FLORELBA)".

    Esquema JSON esperado:
    {JSON_STRUCTURE_PROMPT}

    Texto del reporte a analizar:
    ---
    {ocr_text}
    ---
    """

    try:
        response_text = generate_content(prompt)
        
        # Limpiar la respuesta para asegurarse de que sea solo el JSON
        json_match = re.search(r'```json\n(.*?)\n```', response_text, re.DOTALL)
        if not json_match:
            logger.warning("No se encontró un bloque JSON en la respuesta de Gemini.")
            try:
                return json.loads(response_text)
            except json.JSONDecodeError:
                logger.error("La respuesta de Gemini no es un JSON válido.")
                return None

        cleaned_json = json_match.group(1)
        return json.loads(cleaned_json)

    except Exception as e:
        logger.error(f"Error al parsear el reporte de Travelinkeo con Gemini: {e}")
        return None

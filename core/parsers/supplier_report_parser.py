import logging
import json
from typing import Dict, Any, List
from django.conf import settings
from .ai_engine import get_gemini_client
from ..models.ai_schemas import InformeProveedorSchema

logger = logging.getLogger(__name__)

class SupplierReportParser:
    """
    Servicio de IA para procesar reportes de venta de proveedores (CTG, MY DESTINY, etc.)
    Extrae datos tabulares de texto extraído de PDFs.
    """
    
    SYSTEM_PROMPT = """
    Eres un experto contable de agencias de viajes. Tu tarea es extraer la lista de transacciones de un reporte de ventas de un proveedor.
    
    INSTRUCCIONES:
    1. Identifica el proveedor (ej: CTG o MY DESTINY).
    2. Extrae cada fila de venta/boleto.
    3. Para cada item, identifica:
       - Número de Boleto (13 dígitos).
       - PNR/Localizador (6 caracteres).
       - Pasajero.
       - Tarifa Neta (Neta, Bare, o Fare).
       - Impuestos (TAX).
       - Comisión (Monto de comisión que la agencia recibe).
       - Total a Pagar al proveedor.
    4. La moneda por defecto es USD a menos que se indique lo contrario (ej: VES, VED, Bolívares).
    5. Devuelve la información estrictamente en el formato JSON solicitado.
    """

    def __init__(self):
        self.client = get_gemini_client()

    def parse_report_text(self, text: str) -> Dict[str, Any]:
        """
        Envía el texto del reporte a Gemini para su estructuración.
        """
        try:
            prompt = f"Procesa el siguiente texto de un reporte de proveedor y extrae las transacciones:\n\n{text}"
            
            # Usamos el esquema de Pydantic como guía de respuesta
            response = self.client.generate_content(
                f"{self.SYSTEM_PROMPT}\n\n{prompt}",
                generation_config={
                    "response_mime_type": "application/json",
                    "response_schema": InformeProveedorSchema.model_json_schema()
                }
            )
            
            raw_data = json.loads(response.text)
            
            # Sanación y Validación de Esquema
            from core.services.data_healer import DataHealer
            try:
                validated_data = DataHealer.heal_and_validate(InformeProveedorSchema, raw_data)
                data = validated_data.dict()
            except Exception as e:
                logger.error(f"Fallo de sanación en reporte de proveedor: {e}")
                data = raw_data

            logger.info(f"Reporte de proveedor procesado (Healed): {data.get('proveedor_nombre')}")
            return data
            
        except Exception as e:
            logger.error(f"Error parseando reporte de proveedor con Gemini: {str(e)}")
            return {"proveedor_nombre": "Error", "items": []}

    @staticmethod
    def _apply_universal_schema_filter(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalización adicional si fuera necesaria (similar a ticket_parser)
        """
        # Por ahora los datos vienen limpios por el response_schema de Gemini
        return data

import logging
import json
from typing import Dict, Any, List, Optional
from django.conf import settings
from core.services.ai_engine import ai_engine
from core.models.ai_schemas import InformeProveedorSchema

logger = logging.getLogger(__name__)

class SupplierReportParser:
    """
    Servicio de IA para procesar reportes de venta de proveedores (CTG, MY DESTINY, etc.)
    Extrae datos tabulares de texto o archivos (PDF/Excel) usando Gemini.
    """
    
    SYSTEM_PROMPT = """
    Eres un experto contable de agencias de viajes. Tu tarea es extraer la lista de transacciones de un reporte de ventas de un proveedor.
    
    INSTRUCCIONES:
    1. Identifica el proveedor (ej: CTG, MY DESTINY, CONSOLIDATOR).
    2. Extrae cada fila de venta/boleto.
    3. Para cada item, identifica:
       - Número de Boleto (13 dígitos).
       - PNR/Localizador (6 caracteres).
       - Pasajero.
       - Tarifa Neta (Neta, Bare, o Fare).
       - Impuestos (TAX).
       - Comisión (Monto de comisión que la agencia recibe).
       - Total a Pagar al proveedor (Tarifa Neta + Impuestos - Comisión).
    4. La moneda por defecto es USD a menos que se indique lo contrario (ej: VES, VED, Bolívares).
    5. Devuelve la información estrictamente en el formato JSON solicitado.
    """

    def parse_report_text(self, text: str) -> Dict[str, Any]:
        """
        Envía el texto del reporte a Gemini para su estructuración.
        """
        try:
            logger.info("Enviando texto de reporte a Gemini para parseo estructurado.")
            resultado = ai_engine.call_gemini(
                prompt=f"Procesa el siguiente texto de un reporte de proveedor y extrae las transacciones:\n\n{text}",
                system_instruction=self.SYSTEM_PROMPT,
                response_schema=InformeProveedorSchema,
                feature="supplier_reconciliation"
            )
            
            # El resultado ya viene validado por el schema de AIEngine
            logger.info(f"Reporte de proveedor procesado: {resultado.get('proveedor_nombre')}")
            return resultado
            
        except Exception as e:
            logger.error(f"Error parseando reporte de proveedor con Gemini: {str(e)}")
            return {"proveedor_nombre": "Error", "items": []}

    def parse_report_file(self, file_path: str) -> Dict[str, Any]:
        """
        Analiza un archivo directamente (PDF/Imagen/Texto) usando las capacidades multimodales de Gemini.
        """
        try:
            logger.info(f"Analizando archivo de reporte directamente: {file_path}")
            
            # Si es PDF, podemos intentar enviarlo como media si el SDK lo soporta o extraer texto
            # Por ahora, seguiremos extrayendo texto pero con un prompt más robusto.
            # (En el futuro, podrías usar genai.upload_file aquí)
            
            text = ""
            if file_path.lower().endswith('.pdf'):
                import fitz
                with fitz.open(file_path) as pdf:
                    for page in pdf:
                        t = page.get_text()
                        if t: text += t + "\n"
            else:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    text = f.read()
            
            return self.parse_report_text(text)
            
        except Exception as e:
            logger.error(f"Error parseando archivo de reporte: {e}")
            return {"proveedor_nombre": "Error de archivo", "items": []}

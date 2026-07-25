"""Servicio de invoice parser para la aplicación automation.
"""

import logging

from .ai_engine import analizar_documento_con_gemini_estructurado
from .invoice_schemas import InvoiceDataSchema

logger = logging.getLogger(__name__)


class InvoiceParserService:
    """
    Servicio para parsear facturas de proveedores usando Gemini 1.5 Pro.
    """

    @staticmethod
    def parse_invoice_pdf(pdf_bytes: bytes, mime_type: str = "application/pdf"):
        """
        Envía el PDF a Gemini para extraer datos estructurados.
        """
        system_prompt = (
            "Eres un experto contable de TravelHub. Tu tarea es extraer datos de facturas de proveedores "
            "o liquidaciones de aerolíneas (invoices/statements). "
            "Debes identificar el nombre del proveedor, el número de documento, la fecha de emisión, "
            "la moneda (ISO) y el monto total a pagar. "
            "Sé extremadamente preciso con los decimales."
        )

        user_prompt = "Analiza este documento y extrae la información de facturación siguiendo estrictamente el esquema JSON proporcionado."

        try:
            # Usamos el método especializado para documentos de AIEngine
            result = analizar_documento_con_gemini_estructurado(
                file_bytes=pdf_bytes,
                mime_type=mime_type,
                prompt_text=f"{system_prompt}\n\n{user_prompt}",
                response_schema=InvoiceDataSchema,
            )

            logger.info(
                f"✅ Factura parseada exitosamente: {result.get('numero_factura')} de {result.get('proveedor_nombre')}"
            )
            return result
        except Exception as e:
            logger.error(f"❌ Error parseando factura con Gemini: {e}")
            return None

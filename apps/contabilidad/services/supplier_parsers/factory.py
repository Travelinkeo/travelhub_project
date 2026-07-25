"""Servicio de factory para la aplicación contabilidad.
"""

import logging

from .base_parser import BaseSupplierReportParser
from .ctg_parser import CTGReportParser
from .mydestiny_parser import MyDestinyReportParser

logger = logging.getLogger(__name__)


class SupplierReportParserFactory:
    """
    Factory para obtener la estrategia de parseo adecuada según el proveedor.
    Patrón de Diseño Strategy + Factory.
    """

    @classmethod
    def get_parser(
        cls,
        pdf_bytes: bytes,
        filename: str = "",
        subject: str = "",
        sender_email: str = "",
    ) -> BaseSupplierReportParser | None:
        # get_parser: Obtiene/recupera parser. Args: según implementación. Returns: dato solicitado.
        sender_clean = (sender_email or "").lower()
        subject_clean = (subject or "").lower()
        filename_clean = (filename or "").lower()

        # 1. Detección por Emisor o Asunto
        if "grupoctg" in sender_clean or "ctg" in subject_clean or "ctg" in filename_clean:
            return CTGReportParser(pdf_bytes, filename, subject)

        if (
            "mydestiny" in sender_clean
            or "mydestiny" in subject_clean
            or "my destiny" in subject_clean
            or "my destiny" in filename_clean
        ):
            return MyDestinyReportParser(pdf_bytes, filename, subject)

        # 2. Detección por contenido del PDF (Inspección ligera)
        try:
            import io

            import pypdf

            reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
            first_page_text = reader.pages[0].extract_text() if reader.pages else ""

            if (
                "grupo soporte global" in first_page_text.lower()
                or "client statement" in first_page_text.lower()
            ):
                return CTGReportParser(pdf_bytes, filename, subject)

            if "my destiny" in first_page_text.lower() or "ptys3650" in first_page_text.lower():
                return MyDestinyReportParser(pdf_bytes, filename, subject)

        except Exception as e:
            logger.warning(f"No se pudo inspeccionar contenido PDF para factory: {e}")

        logger.warning(
            f"No se encontró parser para el reporte de proveedor: sender={sender_email}, subject={subject}"
        )
        return None

import concurrent.futures
import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

GOTENBERG_URL = (
    getattr(settings, "GOTENBERG_URL", None) or "http://gotenberg:3000/forms/chromium/convert/html"
)


def _render_with_weasyprint(html_content: str) -> bytes:
    from weasyprint import HTML

    pdf_bytes = HTML(string=html_content, base_url=None).write_pdf()
    return pdf_bytes


class PdfRendererService:
    """
    Servicio centralizado para renderizar HTML a PDF.
    Estrategia:
    1. Gotenberg (Chromium) con timeout de 5s total (incluyendo DNS)
    2. WeasyPrint (local, ~1-3s) si Gotenberg no responde
    """

    @staticmethod
    def render_html_to_pdf(html_content: str, margins: float = 0.0) -> bytes:
        try:
            pdf_bytes = PdfRendererService._try_gotenberg(html_content, margins)
            logger.info(f"Gotenberg genero PDF: {len(pdf_bytes)} bytes")
            return pdf_bytes
        except Exception as e:
            logger.warning(f"Gotenberg fallo o no respondio ({e}), usando WeasyPrint...")

        return PdfRendererService._render_fallback(html_content)

    @staticmethod
    def _try_gotenberg(html_content: str, margins: float) -> bytes:
        width, height = 8.27, 11.7
        payload = {
            "marginTop": str(margins),
            "marginBottom": str(margins),
            "marginLeft": str(margins),
            "marginRight": str(margins),
            "preferCssPageSize": "true",
            "printBackground": "true",
            "paperWidth": str(width),
            "paperHeight": str(height),
        }
        files = {"index.html": ("index.html", html_content, "text/html")}
        session = requests.Session()
        # Enforce short timeouts (3s to connect, 5s to read/render) to prevent long blocks
        response = session.post(GOTENBERG_URL, files=files, data=payload, timeout=(3.0, 5.0))
        response.raise_for_status()
        return response.content


    @staticmethod
    def _render_fallback(html_content: str) -> bytes:
        logger.info("Usando WeasyPrint como fallback local...")
        try:
            pdf_bytes = _render_with_weasyprint(html_content)
            logger.info(f"WeasyPrint genero {len(pdf_bytes)} bytes")
            return pdf_bytes
        except ImportError:
            logger.error("WeasyPrint no esta instalado. No hay forma de generar PDF.")
            raise

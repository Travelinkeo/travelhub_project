"""Servicio de pdf renderer para la aplicación common.
"""

import logging

logger = logging.getLogger(__name__)


def _render_with_weasyprint(html_content: str) -> bytes:
    # _render_with_weasyprint:  render with weasyprint. Args: según implementación. Returns: según implementación.
    from weasyprint import HTML

    pdf_bytes = HTML(string=html_content, base_url=None).write_pdf()
    return pdf_bytes


class PdfRendererService:
    """
    Servicio centralizado para renderizar HTML a PDF.

    ⚙️  ESTRATEGIA:
    Usa WeasyPrint local (no requiere servicio externo).
    Tiempo típico: 1-3s. Sin dependencia de red.

    ❌  Gotenberg eliminado en Fase 5 de optimización.
        WeasyPrint es más barato (sin servicio externo),
        más rápido (sin latencia de red), y más fácil de
        mantener (sin Docker Compose extra).
    """

    @staticmethod
    def render_html_to_pdf(html_content: str, margins: float = 0.0) -> bytes:
        # render_html_to_pdf: Renderiza  html to pdf. Args: contexto/datos. Returns: HTML renderizado.
        try:
            pdf_bytes = _render_with_weasyprint(html_content)
            logger.info(f"WeasyPrint generó {len(pdf_bytes)} bytes")
            return pdf_bytes
        except ImportError:
            logger.error(
                "WeasyPrint no está instalado. "
                "Ejecuta: pip install weasyprint  # o añádelo a requirements/base.txt"
            )
            raise
        except Exception as e:
            logger.error(f"Error generando PDF con WeasyPrint: {e}")
            raise

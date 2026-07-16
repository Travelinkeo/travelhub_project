"""
Servicio para generar PDFs de facturas consolidadas con formato legal venezolano.
"""

import logging

from django.template.loader import render_to_string

# resolved dynamically to avoid circular dependencies
from apps.common.services.pdf_renderer import PdfRendererService
from apps.common.utils.images import get_agencia_logo_b64

logger = logging.getLogger(__name__)


def generar_pdf_factura_consolidada(factura):
    """
    Genera un PDF de la factura consolidada con formato legal venezolano.
    """
    try:
        agencia = factura.agencia
        from django.utils.module_loading import import_string

        is_brand_color_dark = import_string(
            "apps.automation.parsers.ticket_parser.is_brand_color_dark"
        )
        is_dark = is_brand_color_dark(agencia.color_primario) if agencia else True

        plantilla = (
            agencia.plantilla_facturas
            if (agencia and hasattr(agencia, "plantilla_facturas"))
            else "m1"
        )
        plantilla_mapping = {
            "m1": "facturas/variations/v1_classic.html",
            "m2": "facturas/variations/v2_editorial.html",
            "m3": "facturas/variations/v3_executive.html",
            "m4": "facturas/variations/v4_timeline.html",
            "m5": "facturas/variations/v5_modern.html",
        }
        template_path = plantilla_mapping.get(plantilla, "facturas/variations/v1_classic.html")

        from django.template.loader import get_template

        try:
            get_template(template_path)
        except Exception as e:
            logger.warning(f"No se pudo cargar la plantilla {template_path}, usando fallback: {e}")
            template_path = "facturas/factura_consolidada_pdf.html"

        # Renderizar template HTML
        html_string = render_to_string(
            template_path,
            {
                "factura": factura,
                "agencia": agencia,
                "agencia_logo_b64": get_agencia_logo_b64(agencia, is_dark_bg=is_dark),
                "is_dark_color": is_dark,
            },
        )

        # Generar PDF con WeasyPrint
        pdf_file = PdfRendererService.render_html_to_pdf(html_string)

        logger.info(f"PDF generado exitosamente para factura {factura.numero_control}")
        return pdf_file

    except Exception as e:
        logger.error(f"Error generando PDF para factura {factura.numero_control}: {str(e)}")
        raise


def guardar_pdf_factura(factura):
    """
    Genera el PDF de la factura y lo retorna como bytes.

    Args:
        factura: Instancia de Factura

    Returns:
        bytes: Contenido del PDF o None si falla
    """
    try:
        logger.info(f"Iniciando generación de PDF para factura {factura.numero_control}")
        pdf_content = generar_pdf_factura_consolidada(factura)
        logger.info(f"PDF generado, tamaño: {len(pdf_content)} bytes")
        return pdf_content
    except Exception as e:
        logger.error(f"❌ Error guardando PDF: {str(e)}")
        import traceback

        logger.error(traceback.format_exc())
        return None

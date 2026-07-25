"""Servicio de pdf service para la aplicación common.
"""

import logging

from django.apps import apps
from django.core.files.base import ContentFile
from django.template.loader import get_template
from django.utils.module_loading import import_string

from apps.common.utils.images import get_agencia_logo_b64

from .pdf_renderer import PdfRendererService

logger = logging.getLogger(__name__)


def generar_pdf_factura(factura_id: int):
    """
    Genera un archivo PDF para una Factura dada usando Gotenberg.
    """
    Factura = apps.get_model("finance", "Factura")
    try:
        factura = (
            Factura.objects.select_related("cliente", "moneda", "agencia")
            .prefetch_related("items_factura")
            .get(pk=factura_id)
        )
        logger.info(f"Iniciando generación de PDF para Factura ID: {factura.id_factura}")

        agencia = factura.agencia
        if not agencia:
            logger.error(f"❌ ERROR CRÍTICO: Factura {factura_id} no tiene agencia vinculada.")
            return None, None

        plantilla = agencia.plantilla_facturas if hasattr(agencia, "plantilla_facturas") else "m1"
        plantilla_mapping = {
            "m1": "facturas/variations/v1_classic.html",
            "m2": "facturas/variations/v2_editorial.html",
            "m3": "facturas/variations/v3_executive.html",
            "m4": "facturas/variations/v4_timeline.html",
            "m5": "facturas/variations/v5_modern.html",
        }
        template_path = plantilla_mapping.get(plantilla, "facturas/variations/v1_classic.html")
        try:
            template = get_template(template_path)
        except Exception as e:
            logger.warning(f"No se pudo cargar la plantilla {template_path}, usando fallback: {e}")
            template = get_template("facturas/factura_template.html")

        is_brand_color_dark = import_string(
            "apps.automation.parsers.ticket_parser.is_brand_color_dark"
        )
        is_dark = is_brand_color_dark(agencia.color_primario) if agencia else True
        context = {
            "factura": factura,
            "agencia": agencia,
            "is_dark_color": is_dark,
            "agencia_logo_b64": get_agencia_logo_b64(agencia, is_dark_bg=is_dark),
        }
        html_string = template.render(context)

        pdf_bytes = PdfRendererService.render_html_to_pdf(html_string)
        if not pdf_bytes:
            return None, None

        filename = f"Factura-{factura.numero_factura}.pdf"

        # Guardar en el modelo
        factura.archivo_pdf.save(filename, ContentFile(pdf_bytes), save=True)

        logger.info(f"PDF para Factura {factura.numero_factura} generado exitosamente.")
        return pdf_bytes, filename

    except Factura.DoesNotExist:
        logger.error(f"No se encontró la Factura con ID {factura_id}.")
        return None, None
    except Exception as e:
        logger.error(f"Error al generar PDF para Factura ID {factura_id}: {e}", exc_info=True)
        return None, None

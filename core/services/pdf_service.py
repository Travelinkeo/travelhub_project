
import logging
from io import BytesIO

from django.template.loader import get_template

def _get_html_renderer():
    """Lazy loader for WeasyPrint HTML to avoid boot-time hangs."""
    try:
        from weasyprint import HTML
        return HTML
    except Exception as e:
        logger.error(f"Failed to import WeasyPrint: {e}")
        return None


from apps.finance.models import Factura
from core.models import Agencia
from apps.bookings.models import Venta, AlojamientoReserva, AlquilerAutoReserva, ServicioAdicionalDetalle, SegmentoVuelo, TrasladoServicio, ActividadServicio
from core.ticket_parser import is_brand_color_dark

logger = logging.getLogger(__name__)

def _get_agencia():
    """Helper to get the primary agency for branding."""
    return Agencia.objects.filter(pk=1).first() or Agencia.objects.first()

def generar_pdf_factura(factura_id: int):
    """
    Genera un archivo PDF para una Factura dada.

    Args:
        factura_id: El ID de la Factura para la cual generar el PDF.

    Returns:
        Una tupla de (bytes_del_pdf, nombre_del_archivo) o (None, None) si hay un error.
    """
    try:
        factura = Factura.objects.select_related('cliente', 'moneda').prefetch_related('items_factura').get(pk=factura_id)
        logger.info(f"Iniciando generación de PDF para Factura ID: {factura.id_factura}")

        agencia = factura.agencia or _get_agencia()
        is_dark = is_brand_color_dark(agencia.color_primario) if agencia else True

        template = get_template('facturas/factura_template.html')
        context = {
            'factura': factura,
            'agencia': agencia,
            'is_dark_color': is_dark,
        }
        html_string = template.render(context)

        HTML_renderer = _get_html_renderer()
        if not HTML_renderer:
            logger.error("WeasyPrint is not available.")
            return None, None
            
        pdf_bytes = HTML_renderer(string=html_string).write_pdf()
        
        filename = f"Factura-{factura.numero_factura}.pdf"

        # GUARDAR EN EL MODELO PARA ACTIVAR TELEGRAM
        from django.core.files.base import ContentFile
        # Solo guardar si no existe o si queremos sobrescribir siempre (mejor sobrescribir para updates)
        factura.archivo_pdf.save(filename, ContentFile(pdf_bytes), save=True)

        logger.info(f"PDF para Factura {factura.numero_factura} generado y GUARDADO exitosamente.")
        return pdf_bytes, filename

    except Factura.DoesNotExist:
        logger.error(f"No se encontró la Factura con ID {factura_id} para generar el PDF.")
        return None, None
    except Exception as e:
        logger.error(f"Error inesperado al generar PDF para Factura ID {factura_id}: {e}", exc_info=True)
        return None, None

def generar_pdf_voucher_unificado(venta_id: int):
    """
    Genera un archivo PDF de voucher unificado para una Venta dada.

    Args:
        venta_id: El ID de la Venta para la cual generar el PDF del voucher.

    Returns:
        Una tupla de (bytes_del_pdf, nombre_del_archivo) o (None, None) si hay un error.
    """
    try:
        venta = Venta.objects.select_related('cliente', 'moneda', 'agencia').get(pk=venta_id)
        agencia = venta.agencia or _get_agencia()
        is_dark = is_brand_color_dark(agencia.color_primario) if agencia else True

        voucher_data = {
            'venta': venta,
            'agencia': agencia,
            'is_dark_color': is_dark,
            'alojamientos': venta.alojamientos.all(),
            'alquileres_autos': venta.alquileres_autos.all(),
            'servicios_adicionales': venta.servicios_adicionales.all(),
            'segmentos_vuelo': venta.segmentos_vuelo.all(),
            'traslados': venta.traslados.all(),
            'actividades': venta.actividades.all(),
        }

        # Selección dinámica de plantilla basada en configuración de la agencia
        model_code = getattr(agencia, 'plantilla_vouchers', 'm1')
        templates_map = {
            'm1': 'vouchers/variations/v1_golden_classic.html',
            'm2': 'vouchers/variations/v2_editorial.html',
            'm3': 'vouchers/variations/v3_executive.html',
            'm4': 'vouchers/variations/v4_timeline.html',
            'm5': 'vouchers/variations/v5_modern.html',
        }
        template_path = templates_map.get(model_code, 'vouchers/variations/v1_golden_classic.html')
        
        template = get_template(template_path)
        html_string = template.render(voucher_data)

        HTML_renderer = _get_html_renderer()
        if not HTML_renderer:
            logger.error("WeasyPrint is not available.")
            return None, None

        pdf_bytes = HTML_renderer(string=html_string).write_pdf()
        
        filename = f"Voucher-{venta.localizador or venta.id_venta}.pdf"

        logger.info(f"PDF de voucher para Venta {venta.id_venta} generado exitosamente.")
        return pdf_bytes, filename

    except Venta.DoesNotExist:
        logger.error(f"No se encontró la Venta con ID {venta_id} para generar el PDF del voucher.")
        return None, None
    except Exception as e:
        logger.error(f"Error inesperado al generar PDF de voucher para Venta ID {venta_id}: {e}", exc_info=True)
        return None, None

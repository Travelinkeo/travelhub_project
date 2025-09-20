
import logging
from io import BytesIO

from django.template.loader import get_template
from weasyprint import HTML

from core.models.facturacion import Factura
from core.models.ventas import Venta, AlojamientoReserva, AlquilerAutoReserva, ServicioAdicionalDetalle, SegmentoVuelo, TrasladoServicio, ActividadServicio

logger = logging.getLogger(__name__)

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

        template = get_template('facturas/factura_template.html')
        context = {
            'factura': factura,
        }
        html_string = template.render(context)

        pdf_bytes = HTML(string=html_string).write_pdf()
        
        filename = f"Factura-{factura.numero_factura}.pdf"

        logger.info(f"PDF para Factura {factura.numero_factura} generado exitosamente.")
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
        venta = Venta.objects.get(pk=venta_id)
        logger.info(f"Iniciando generación de PDF de voucher para Venta ID: {venta.id_venta}")

        # Aquí se recopilarán todos los datos necesarios de la venta y sus componentes
        # para pasarlos al template.
        voucher_data = {
            'venta': venta,
            'alojamientos': AlojamientoReserva.objects.filter(venta=venta).all(),
            'alquileres_autos': AlquilerAutoReserva.objects.filter(venta=venta).all(),
            'servicios_adicionales': ServicioAdicionalDetalle.objects.filter(venta=venta).all(),
            'segmentos_vuelo': SegmentoVuelo.objects.filter(venta=venta).all(),
            'traslados': TrasladoServicio.objects.filter(venta=venta).all(),
            'actividades': ActividadServicio.objects.filter(venta=venta).all(),
            # ... otros componentes que puedan existir
        }

        template = get_template('vouchers/unified_voucher_template.html')
        html_string = template.render(voucher_data)

        pdf_bytes = HTML(string=html_string).write_pdf()
        
        filename = f"Voucher-{venta.localizador or venta.id_venta}.pdf"

        logger.info(f"PDF de voucher para Venta {venta.id_venta} generado exitosamente.")
        return pdf_bytes, filename

    except Venta.DoesNotExist:
        logger.error(f"No se encontró la Venta con ID {venta_id} para generar el PDF del voucher.")
        return None, None
    except Exception as e:
        logger.error(f"Error inesperado al generar PDF de voucher para Venta ID {venta_id}: {e}", exc_info=True)
        return None, None

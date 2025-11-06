"""
Servicio para generar PDFs de facturas consolidadas con formato legal venezolano.
"""

import os
from django.template.loader import render_to_string
from django.conf import settings
from weasyprint import HTML
import logging

logger = logging.getLogger(__name__)


def generar_pdf_factura_consolidada(factura):
    """
    Genera un PDF de la factura consolidada con formato legal venezolano.
    
    Args:
        factura: Instancia de FacturaConsolidada
        
    Returns:
        bytes: Contenido del PDF generado
    """
    try:
        # Renderizar template HTML
        html_string = render_to_string(
            'facturas/factura_consolidada_pdf.html',
            {'factura': factura}
        )
        
        # Generar PDF con WeasyPrint
        pdf_file = HTML(string=html_string).write_pdf()
        
        logger.info(f"PDF generado exitosamente para factura {factura.numero_factura}")
        return pdf_file
        
    except Exception as e:
        logger.error(f"Error generando PDF para factura {factura.numero_factura}: {str(e)}")
        raise


def guardar_pdf_factura(factura):
    """
    Genera y guarda el PDF de la factura en el campo archivo_pdf.
    
    Args:
        factura: Instancia de FacturaConsolidada
        
    Returns:
        bool: True si se guardó exitosamente
    """
    try:
        from django.core.files.base import ContentFile
        from django.core.files.storage import default_storage
        
        logger.info(f"Iniciando generación de PDF para factura {factura.numero_factura}")
        logger.info(f"Storage backend: {default_storage.__class__.__name__}")
        logger.info(f"USE_CLOUDINARY: {settings.USE_CLOUDINARY}")
        
        # Generar PDF
        pdf_content = generar_pdf_factura_consolidada(factura)
        logger.info(f"PDF generado, tamaño: {len(pdf_content)} bytes")
        
        # Nombre del archivo
        filename = f"factura_{factura.numero_factura.replace('/', '_')}.pdf"
        logger.info(f"Nombre de archivo: {filename}")
        
        # Guardar en el modelo
        factura.archivo_pdf.save(filename, ContentFile(pdf_content), save=True)
        
        # Verificar que se guardó
        if factura.archivo_pdf:
            url = factura.archivo_pdf.url
            logger.info(f"✅ PDF guardado exitosamente")
            logger.info(f"   Ruta: {factura.archivo_pdf.name}")
            logger.info(f"   URL: {url}")
            logger.info(f"   Storage: {factura.archivo_pdf.storage.__class__.__name__}")
        else:
            logger.warning("⚠️ archivo_pdf está vacío después de guardar")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error guardando PDF: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

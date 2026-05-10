from django.template.loader import render_to_string
from apps.cotizaciones.models import Cotizacion
from core.services.pdf_renderer import PdfRendererService

def generar_pdf_cotizacion(cotizacion: Cotizacion):
    """
    Renderiza una cotización a HTML y luego a un PDF usando Gotenberg.
    Devuelve el contenido del PDF en bytes.
    """
    context = {
        'cotizacion': cotizacion
    }
    # Render the HTML template
    html_string = render_to_string('cotizaciones/plantilla_cotizacion.html', context)
    
    # Generate the PDF using central service
    pdf_bytes = PdfRendererService.render_html_to_pdf(html_string)
    
    return pdf_bytes

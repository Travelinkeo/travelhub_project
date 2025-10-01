from django.template.loader import render_to_string
from weasyprint import HTML
from .models import Cotizacion

def generar_pdf_cotizacion(cotizacion: Cotizacion):
    """
    Renderiza una cotización a HTML y luego a un PDF.
    Devuelve el contenido del PDF en bytes.
    """
    context = {
        'cotizacion': cotizacion
    }
    # Render the HTML template
    html_string = render_to_string('cotizaciones/plantilla_cotizacion.html', context)
    
    # Create a WeasyPrint HTML object
    html = HTML(string=html_string)
    
    # Generate the PDF
    pdf_bytes = html.write_pdf()
    
    return pdf_bytes

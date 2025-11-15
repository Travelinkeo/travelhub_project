from django.template.loader import render_to_string
try:
    from weasyprint import HTML
    WEASYPRINT_AVAILABLE = True
except (ImportError, OSError):
    WEASYPRINT_AVAILABLE = False
    HTML = None
from .models import Cotizacion

def generar_pdf_cotizacion(cotizacion: Cotizacion):
    """
    Renderiza una cotización a HTML y luego a un PDF.
    Devuelve el contenido del PDF en bytes.
    """
    if not WEASYPRINT_AVAILABLE:
        raise RuntimeError(
            "WeasyPrint no está disponible. Instala las dependencias del sistema: "
            "apt-get install libpango-1.0-0 libpangoft2-1.0-0 libgdk-pixbuf2.0-0 libgobject-2.0-0"
        )
    
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

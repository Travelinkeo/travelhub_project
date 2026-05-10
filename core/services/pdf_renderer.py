import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)

# Gotenberg Configuration (Chromium Headless)
GOTENBERG_URL = getattr(settings, 'GOTENBERG_URL', 'http://gotenberg:3000/forms/chromium/convert/html')

class PdfRendererService:
    """
    Servicio centralizado para renderizar HTML a PDF usando Gotenberg.
    """
    
    @staticmethod
    def check_health() -> bool:
        """
        Verifica si el servicio de Gotenberg está disponible.
        """
        try:
            # El endpoint de salud de Gotenberg suele ser /health
            # Pero depende de la configuración. Intentaremos el base URL
            health_url = GOTENBERG_URL.split('/forms')[0] + '/health'
            response = requests.get(health_url, timeout=5)
            return response.status_code == 200
        except Exception:
            return False

    @staticmethod
    def render_html_to_pdf(html_content: str, paper_size: str = 'A4', margins: float = 0.0) -> bytes:
        """
        Envía HTML a Gotenberg y devuelve los bytes del PDF generado.
        
        Args:
            html_content: El contenido HTML completo a renderizar.
            paper_size: 'A4' (default) o dimensiones personalizadas.
            margins: Margen en pulgadas (default 0.0 para vouchers/facturas con diseño propio).
            
        Returns:
            bytes: Contenido del PDF.
            
        Raises:
            Exception: Si falla la comunicación con Gotenberg.
        """
        try:
            files = {
                'index.html': ('index.html', html_content)
            }
            
            # Dimensiones A4 en pulgadas
            width, height = 8.27, 11.7
            
            payload = {
                'marginTop': str(margins),
                'marginBottom': str(margins),
                'marginLeft': str(margins),
                'marginRight': str(margins),
                'preferCssPageSize': 'true',
                'printBackground': 'true',
                'paperWidth': str(width),
                'paperHeight': str(height),
            }
            
            logger.info(f"🖨️ Enviando HTML a Gotenberg para renderizado PDF ({len(html_content)} chars)")
            
            response = requests.post(GOTENBERG_URL, files=files, data=payload, timeout=30)
            response.raise_for_status()
            
            return response.content
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Error de red al llamar a Gotenberg: {e}")
            raise Exception(f"Error de comunicación con el motor de PDF: {e}")
        except Exception as e:
            logger.error(f"❌ Fallo crítico en renderizado PDF: {e}", exc_info=True)
            raise Exception(f"Fallo en la generación del documento PDF: {e}")

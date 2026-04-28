import logging
import os
import datetime as dt
from typing import Dict, Any, Tuple
from typing import Dict, Any, Tuple
# from jinja2 import Environment, FileSystemLoader, select_autoescape

# Importación condicional segura de WeasyPrint
try:
    from weasyprint import HTML as WeasyHTML
except ImportError:
    WeasyHTML = None

logger = logging.getLogger(__name__)

class PdfGenerationService:
    """
    Microservicio dedicado a la renderización de boletos en formato PDF A4.
    Responsabilidad Única: Templates y conversión binaria.
    """
    
    @staticmethod
    def generate_ticket(data: Dict[str, Any], agencia_obj=None) -> Tuple[bytes, str]:
        if not WeasyHTML:
             logger.error("WeasyPrint no está instalado. No se puede generar el PDF.")
             return b"", "error_weasyprint.pdf"
            
        # Determinar base_dir relativo a este archivo
        # (core/services/parsers/pdf_generation.py -> core -> travelhub_project)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_dir))) 
        
        from django.template.loader import render_to_string
        
        # Selección de plantilla
        source_system = data.get('SOURCE_SYSTEM', 'KIU').upper()
        template_name = "core/tickets/golden_ticket_v2.html"
        
        # Inyección de contexto
        context = PdfGenerationService._build_context(data, agencia_obj, source_system)
        
        # Renderizado HTML
        try:
            html_out = render_to_string(template_name, context)
            
            # Conversión a PDF
            logger.info(f"🖨️ Generando PDF en memoria para PNR: {context.get('CODIGO_RESERVA')}")
            pdf_bytes = WeasyHTML(string=html_out).write_pdf()
            
            # Nombre de archivo
            timestamp = dt.datetime.now().strftime("%Y%m%d%H%M%S")
            num_boleto = data.get('NUMERO_DE_BOLETO') or "SIN_NUMERO"
            fname = f"Boleto_{num_boleto}_{timestamp}.pdf"
            
            return pdf_bytes, fname
        except Exception as e:
            logger.error(f"Fallo en renderizado/generación de PDF via Django Engine: {e}", exc_info=True)
            return b"", "error_generacion.pdf"

    @staticmethod
    def _build_context(data: Dict[str, Any], agencia_obj, source_system: str) -> dict:
        """Construye el diccionario de datos requerido por la plantilla Jinja2."""
        
        nombre_pasajero = data.get('NOMBRE_DEL_PASAJERO') or data.get('passenger_name') or \
                          data.get('nombre_pasajero_completo') or data.get('nombre_completo')
        
        if isinstance(data.get('pasajero'), dict):
            nombre_pasajero = nombre_pasajero or data.get('pasajero').get('nombre_completo')

        f_emision = data.get('FECHA_DE_EMISION') or data.get('fecha_emision')
        if not f_emision or str(f_emision).strip().lower() == 'no encontrado':
            f_emision = dt.datetime.now().strftime("%d %b %Y").upper()

        return {
            'agencia': agencia_obj,
            'NOMBRE_DEL_PASAJERO': nombre_pasajero,
            'CODIGO_IDENTIFICACION': data.get('CODIGO_IDENTIFICACION') or data.get('FOID') or data.get('passenger_document'),
            'NUMERO_DE_BOLETO': data.get('NUMERO_DE_BOLETO') or data.get('ticket_number') or data.get('numero_boleto'),
            'FECHA_DE_EMISION': f_emision,
            'CODIGO_RESERVA': data.get('CODIGO_RESERVA') or data.get('SOLO_CODIGO_RESERVA') or data.get('pnr') or data.get('localizador_pnr'),
            'CODIGO_RESERVA_AEROLINEA': data.get('CODIGO_RESERVA_AEROLINEA') or data.get('codigo_reserva_aerolinea'),
            'NOMBRE_AEROLINEA': data.get('NOMBRE_AEROLINEA') or data.get('nombre_aerolinea') or data.get('issuing_airline') or "AEROLINEA",
            'SOURCE_SYSTEM': source_system.replace("AI_", ""),
            'TARIFA_BASE': data.get('TARIFA_IMPORTE') or data.get('fare_amount') or data.get('tarifa_base') or "0.00",
            'TOTAL': data.get('TOTAL') or data.get('total_amount') or data.get('total_boleto') or "0.00",
            'TOTAL_MONEDA': data.get('TOTAL_MONEDA') or data.get('moneda') or data.get('total_currency') or 'USD',
            'AGENTE_EMISOR': data.get('AGENTE_EMISOR') or (agencia_obj.nombre_comercial if agencia_obj else "AGENCIA"),
            'NUMERO_IATA': data.get('NUMERO_IATA') or "N/A",
            'vuelos': data.get('segmentos') or data.get('vuelos') or data.get('itinerario') or data.get('flights') or [],
            'solo_nombre_pasajero': data.get('SOLO_NOMBRE_PASAJERO') or data.get('solo_nombre_pasajero') or "Viajero",
            'es_remision': data.get('es_remision', False),
            'is_dark_color': PdfGenerationService._is_dark_color(agencia_obj.color_primario if agencia_obj and agencia_obj.color_primario else '#0D1E40')
        }

    @staticmethod
    def _is_dark_color(hex_color: str) -> bool:
        """Calcula si un color hexadecimal es oscuro usando el algoritmo YIQ."""
        try:
            hex_color = str(hex_color).lstrip('#')
            if len(hex_color) == 3:
                hex_color = ''.join([c*2 for c in hex_color])
            r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
            yiq = ((r * 299) + (g * 587) + (b * 114)) / 1000
            return yiq < 128
        except Exception:
            return True # Por defecto oscuro (B2B Classic)

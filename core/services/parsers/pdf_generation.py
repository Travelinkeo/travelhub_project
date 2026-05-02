import logging
import os
import datetime as dt
from typing import Dict, Any, Tuple
import requests

# Importación condicional segura de WeasyPrint
# Movida dentro del método para evitar bloqueos en el arranque

logger = logging.getLogger(__name__)

class PdfGenerationService:
    """
    Microservicio dedicado a la renderización de boletos en formato PDF A4.
    Fuerza el uso de WeasyPrint para garantizar la calidad profesional y márgenes cero
    que el usuario tenía anteriormente.
    """
    
    @staticmethod
    def generate_ticket(data: Dict[str, Any], agencia_obj=None, **kwargs) -> Tuple[bytes, str]:
        from django.template.loader import render_to_string
        try:
            from weasyprint import HTML as WeasyHTML
        except (ImportError, OSError):
            WeasyHTML = None
        
        # Selección de plantilla
        source_system = data.get('SOURCE_SYSTEM', 'KIU').upper()
        template_name = "core/tickets/golden_ticket_v2.html"
        
        # Inyección de contexto
        context = PdfGenerationService._build_context(data, agencia_obj, source_system)
        
        # Renderizado HTML
        try:
            html_out = render_to_string(template_name, context)
            
            # --- PRIORIDAD 1: WEASYPRINT (Calidad Original) ---
            if WeasyHTML:
                logger.info(f"🖨️ Generando PDF con WEASYPRINT para PNR: {context.get('CODIGO_RESERVA')}")
                pdf_bytes = WeasyHTML(string=html_out).write_pdf()
            else:
                # --- FALLBACK: GOTENBERG (Si WeasyPrint falla) ---
                logger.warning("⚠️ WeasyPrint no disponible. Usando Gotenberg (Chromium).")
                GOTENBERG_URL = "http://gotenberg:3000/forms/chromium/convert/html"
                files = {'index.html': html_out}
                payload = {
                    'marginTop': '0',
                    'marginBottom': '0',
                    'marginLeft': '0',
                    'marginRight': '0',
                    'paperWidth': '8.27',
                    'paperHeight': '11.69',
                    'preferCSSPageSize': 'true'
                }
                resp = requests.post(GOTENBERG_URL, files=files, data=payload, timeout=30)
                if resp.status_code == 200:
                    pdf_bytes = resp.content
                else:
                    raise Exception(f"Gotenberg error {resp.status_code}: {resp.text}")

            # Nombre de archivo profesional
            timestamp = dt.datetime.now().strftime("%Y%m%d%H%M%S")
            num_boleto = data.get('NUMERO_DE_BOLETO') or data.get('ticket_number') or data.get('numero_boleto') or "S-N"
            fname = f"Boleto_{num_boleto}_{timestamp}.pdf"
            
            return pdf_bytes, fname
        except Exception as e:
            logger.error(f"Fallo en renderizado/generación de PDF: {e}", exc_info=True)
            return b"", "error_generacion.pdf"

    @staticmethod
    def _build_context(data: Dict[str, Any], agencia_obj, source_system: str) -> dict:
        """Construye el contexto para la plantilla."""
        
        # Lógica de nombre para el saludo (Separar por /)
        solo_nombre = data.get('solo_nombre_pasajero') or data.get('first_name') or data.get('SOLO_NOMBRE_PASAJERO')
        
        nombre_original = data.get('NOMBRE_DEL_PASAJERO') or data.get('passenger_name') or \
                          data.get('nombre_pasajero_completo') or data.get('nombre_completo') or "VIAJERO"

        if not solo_nombre:
            if '/' in nombre_original:
                parts = nombre_original.split('/')
                if len(parts) > 1:
                    full_first_name = parts[1].strip()
                    import re
                    solo_nombre = re.sub(r'\s+(MR|MRS|MS|MSTR|MISS|M|F)$', '', full_first_name, flags=re.IGNORECASE).split(' ')[0]
                else:
                    solo_nombre = parts[0].strip().split(' ')[0]
            else:
                solo_nombre = nombre_original.split(' ')[0]
        
        # Limpieza final
        solo_nombre = str(solo_nombre).strip().upper() if solo_nombre else "VIAJERO"

        f_emision = data.get('FECHA_DE_EMISION') or data.get('fecha_emision')
        if not f_emision or str(f_emision).strip().lower() == 'no encontrado':
            f_emision = dt.datetime.now().strftime("%d %b %Y").upper()

        agente = data.get('AGENTE_EMISOR') or data.get('agencia_nombre')
        if not agente and agencia_obj:
            agente = agencia_obj.iata or agencia_obj.nombre_comercial
        
        # Localizador de aerolínea (si no está al top-level, buscar en segmentos)
        loc_aero = data.get('CODIGO_RESERVA_AEROLINEA') or data.get('airline_pnr') or data.get('pnr_aerolinea')
        if not loc_aero:
            vuelos = data.get('segmentos') or data.get('vuelos') or []
            if vuelos and isinstance(vuelos, list) and len(vuelos) > 0:
                loc_aero = vuelos[0].get('localizador_aerolinea') or vuelos[0].get('airline_pnr')

        return {
            'agencia': agencia_obj,
            'NOMBRE_DEL_PASAJERO': nombre_original,
            'CODIGO_IDENTIFICACION': data.get('CODIGO_IDENTIFICACION') or data.get('FOID') or data.get('passenger_document') or data.get('foid_pasajero'),
            'NUMERO_DE_BOLETO': data.get('NUMERO_DE_BOLETO') or data.get('ticket_number') or data.get('numero_boleto'),
            'FECHA_DE_EMISION': f_emision,
            'CODIGO_RESERVA': data.get('CODIGO_RESERVA') or data.get('pnr') or data.get('localizador_pnr'),
            'CODIGO_RESERVA_AEROLINEA': loc_aero,
            'NOMBRE_AEROLINEA': data.get('NOMBRE_AEROLINEA') or data.get('nombre_aerolinea') or data.get('aerolinea_emisora') or data.get('issuing_airline') or data.get('airline') or "AEROLINEA",
            'SOURCE_SYSTEM': source_system.replace("AI_", ""),
            'TARIFA_BASE': data.get('TARIFA_IMPORTE') or data.get('fare_amount') or data.get('tarifa_base') or "0.00",
            'TOTAL': data.get('TOTAL') or data.get('total_amount') or data.get('total_boleto') or "0.00",
            'TOTAL_MONEDA': data.get('TOTAL_MONEDA') or data.get('moneda') or data.get('total_currency') or 'USD',
            'AGENTE_EMISOR': agente or "10617390",
            'vuelos': data.get('segmentos') or data.get('vuelos') or data.get('itinerario') or data.get('flights') or [],
            'solo_nombre_pasajero': solo_nombre,
            'es_remision': data.get('es_remision', False),
            'is_dark_color': PdfGenerationService._is_dark_color(agencia_obj.color_primario if agencia_obj and agencia_obj.color_primario else '#0D1E40')
        }

    @staticmethod
    def _is_dark_color(hex_color: str) -> bool:
        try:
            hex_color = str(hex_color).lstrip('#')
            if len(hex_color) == 3: hex_color = ''.join([c*2 for c in hex_color])
            r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
            yiq = ((r * 299) + (g * 587) + (b * 114)) / 1000
            return yiq < 128
        except: return True

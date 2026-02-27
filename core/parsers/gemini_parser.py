
import os
import json
import logging
import google.generativeai as genai
from django.conf import settings
from .base_parser import BaseTicketParser, ParsedTicketData

logger = logging.getLogger(__name__)

class GeminiParser(BaseTicketParser):
    """
    Parser basado en IA (Google Gemini) para extraer datos de boletos aéreos.
    No usa Regex. Usa Comprensión de Lenguaje Natural.
    """
    
    def __init__(self):
        # Configurar API Key
        api_key = os.getenv('GEMINI_API_KEY') or getattr(settings, 'GEMINI_API_KEY', None)
        if not api_key:
            logger.error("GEMINI_API_KEY no encontrada.")
            self.model = None
            return

        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash')

    def can_parse(self, text: str) -> bool:
        # Gemini puede parsear CUALQUIER boleto, siempre que haya texto legíble.
        # Pero para evitar gastos innecesarios, podemos limitar o dejarlo como "True" si es el parser por defecto.
        return len(text) > 50

    def parse(self, text: str, html_text: str = "", pdf_path: str = None) -> ParsedTicketData:
        if not self.model:
            logger.error("Modelo Gemini no inicializado (Falta API Key)")
            return {}

        prompt_text = f"""
        Actúa como un experto en extracción de datos de boletos aéreos (GDS Sabre, Amadeus, Kiu).
        Tu tarea es extraer entidades estructuradas del siguiente boleto aéreo.
        
        Reglas Críticas:
        1. Ignora el nombre de la aerolínea si está pegado a la ciudad. Normaliza nombres (AEROVIAS DEL CONTINENTE -> AVIANCA).
        2. FECHAS: Normaliza a "DD MMM YY" o "DD MMM YY HH:MM".
        3. RESPETA LOS ENCABEZADOS DE COLUMNA: SALIDA = Hora Salida. LLEGADA = Hora Llegada.
        4. Busca el código de reserva (PNR) de 6 caracteres alfanuméricos.
           - Si ves "KW23RU / F1", el PNR es SOLO "KW23RU".
           - Si ves "Booking Ref: C1/QJHLNP", el PNR es "QJHLNP" (Ignora el 'C1/').
           - Si el texto comienza con "Itinerary for Record Locator XXXXXX", ese es el PNR.
        5. Extrae la franquicia de equipaje (Ej: "1PC", "23KG") si existe. Si no, usa "N/A".
        6. LOCALIZADOR AEROLÍNEA (Secondary PNR):
           - Busca explícitamente "Copa Airlines Record Locator [CODE]". Ese [CODE] es el localizador de la aerolínea.
           - Diferéncialo del PNR principal. 
        7. IDENTIFICA EL SISTEMA GDS DE ORIGEN:
           - Si ves "ISSUING AIRLINE : AEROLINEAS ESTELAR", es "ESTELAR_WEB" (aunque diga E-TICKET).
           - Si ves "ISSUING AIRLINE : RUTACA", es "RUTACA_WEB".
           - Si ves "ISSUING AIRLINE : AVIOR" o "AVIOR AIRLINES", es "KIU".
           - Si ves "OFFICE ID: VE-..." o "RIF: J...", es "ESTELAR_WEB" o "KIU" o "RUTACA_WEB".
           - Si ves "RECIBO DE PASAJE ELECTRÓNICO" con diseño de tabla, suele ser SABRE.
           - Si ves "SPRK" o "COPA AIRLINES" o "Itinerary for Record Locator" con logo de Copa o formato Copa, es COPA_SPRK.
           - Si hay garbage value "(cid:..)" en el texto pero ves la imagen, USA LA IMAGEN.
        8. EXTRAE EL TOTAL DEL BOLETO (Monto final).
        9. EXTRAE NÚMERO DE BOLETO (13 dígitos):
           - COPA: Busca "ETKT", "eTicket" o "Ticket Number". Empieza con 230.
           - RUTACA/ESTELAR: Busca "TICKET NRO", "BOLETO", "TKT".
           - Si hay varios, usa el primero. SIEMPRE PONES SOLO DIGITOS (13).
        10. DIRECCION AEROLINEA:
            - Busca la línea que empiece con "ADDRESS/DIRECCION" o "ADDRESS".
            - Extrae TODO lo que sigue después de los dos puntos ":". Ej: "AV JORGE RODRIGUEZ...".
            - Si no está ese encabezado, busca al pie de página.
        11. AGENTE EMISOR / IATA / OFFICE ID:
           - BUSCA EL "OFFICE ID" o "CÓDIGO IATA" de la agencia (ej: "BLA005RSJ", "PTYN682EM", "CCS00ESKA").
           - PRIORIDAD MAXIMA: El código alfanumérico de 8-9 caracteres.
           - SI NO ENCUENTRAS CÓDIGO, deja el campo con el nombre de la agencia.
           - EJEMPLO RUTACA/AVIOR: "BLA005RSJ".

        12. REFERENCIA DE AEROLINEAS KIU (IATA -> NOMBRE):
           - Usa esta lista para corregir o inferir el nombre completo de la aerolínea si solo ves el código o un nombre parcial:
           - 5R: RUTACA
           - 7N: PAWA DOMINICANA
           - 7P: AIR PANAMA
           - 9R: SATENA
           - 9V: AVIOR AIRLINES C A
           - A6: PEGASO TRAVEL LLC
           - C3: CARGOTHREE
           - CV: AEROCARIBE
           - CW: AEROPOSTAL ALAS DE VENEZUELA CA
           - DO: SKY HIGH
           - E4: ESTELAR LATINOAMERICA
           - ES: ESTELAR
           - G0: ALIANZA GLANCELOT C A
           - G6: GLOBAL
           - GI: FLY THE WORLD
           - L5: RED AIR
           - NU: MUNDO AIRWAYS
           - O3: SASCA AIRLINES
           - PU: PLUS ULTRA
           - QL: LASER AIRLINES
           - RU: GLOBAL
           - T5: TURPIAL
           - T7: SKY ATLANTIC TRAVEL US.
           - T9: TURPIAL AIRLINES CA
           - V0: CONVIASA
           - WW: RUTAS AEREAS DE VENEZUELA
        
        Texto del Boleto (puede estar corrupto si es PDF viejo):
        \"\"\"
        {text[:15000]}
        \"\"\"
        
        Responde SOLAMENTE con un JSON válido con esta estructura:
        {{
            "razonamiento": "...",
            "gds_detected": "...", 
            "pnr": "...",
            "localizador_aerolinea": "...",
            "fecha_emision": "...",
            "numero_boleto": "...",
            "pasajero": {{ "nombre_completo": "...", "documento_identidad": "..." }},
            "vuelos": [ {{ "aerolinea": "...", "numero_vuelo": "...", "origen": "...", "destino": "...", "fecha_salida": "...", "hora_salida": "...", "fecha_llegada": "...", "hora_llegada": "...", "equipaje": "..." }} ],
            "agencia": "...", 
            "agente_emisor": "...",
            "agencia_iata": "...",
            "direccion_aerolinea": "...",
            "total": "...",
            "total_moneda": "..."
        }}
        """

        content_parts = [prompt_text]
        
        # --- VISION SUPPORT ---
        # Si hay pdf_path y el texto parece corrupto (cid:) o muy corto, usamos visión.
        use_vision = False
        if pdf_path and ('(cid:' in text or len(text) < 100 or 'cid:1' in text):
             try:
                 import pypdfium2 as pdfium
                 logger.info(f"👁️ Detectado texto corrupto o PDF complejo. Usando Gemini Vision con: {pdf_path}")
                 
                 pdf = pdfium.PdfDocument(pdf_path)
                 if len(pdf) > 0:
                     # Renderizar primera página a imagen
                     pil_image = pdf[0].render(scale=2).to_pil()
                     content_parts.append(pil_image)
                     use_vision = True
                     
                     # Si hay segunda página y es ticket largo, tal vez necesitemos más, pero página 1 suele tener todo.
             except Exception as e:
                 logger.error(f"❌ Error renderizando PDF para Vision: {e}")
        
        try:
            response = self.model.generate_content(content_parts)
            json_str = response.text.replace('```json', '').replace('```', '').strip()
            data = json.loads(json_str)
            if use_vision:
                 data['vision_used'] = True
                 logger.info("✅ Parseo exitoso usando Gemini Vision.")
            return data
        except Exception as e:
            logger.error(f"Error parsing with Gemini: {e}")
            try:
                pass # logger.error(f"Raw Response: {response.text[:500]}...")
            except:
                pass
            return {}

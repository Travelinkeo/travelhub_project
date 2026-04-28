import logging
import datetime
# import google.generativeai as genai # Moved to lazy import
from django.conf import settings
from django.utils import timezone
from apps.bookings.models import Venta
from apps.bookings.models import BoletoImportado

logger = logging.getLogger(__name__)

class LinkeoService:
    """
    Service for handling AI-driven chat interactions ("Linkeo").
    Uses Gemini for intent classification and entity extraction.
    """
    
    INTENTS = {
        'QUERY_SALES': ['ventas', 'cuanto vendi', 'cierre', 'total del dia'],
        'CHECK_TICKET': ['estatus boleto', 'como va el boleto', 'revisar boleto'],
        'GENERAL': ['hola', 'gracias', 'adios']
    }

    @staticmethod
    def _get_gemini_model():
        try:
            import google.generativeai as genai
            api_key = getattr(settings, 'GEMINI_API_KEY', None)
            if not api_key:
                logger.warning("Gemini API Key not found.")
                return None
            # Usamos el alias 'gemini-flash-latest' que está validado en la lista de modelos disponibles
            return genai.GenerativeModel('gemini-flash-latest')
        except ImportError:
            logger.error("google-generativeai library not installed.")
            return None
        except Exception as e:
            logger.error(f"Error configuring Gemini: {e}")
            return None

    @classmethod
    def process_message(cls, text: str, user_id: int = None) -> str:
        """
        Main entry point. Receives text, returns a response string.
        """
        # ... existing classification code ... (omitted for brevity, will be preserved by logic if I don't touch it)
        # Wait, I cannot omit code in REPLACE_FILE_CONTENT unless I target specific lines.
        # I am targeting _get_gemini_model and _handle_ai_chat mainly.
        # Let's target _get_gemini_model first.
        pass 
    
    # Actually, I'll do two separate replacements or one large block if contiguous.
    # They are not contiguous. I'll make two edits using AllowMultiple=True? No, tool says "Use this tool ONLY when you are making a SINGLE CONTIGUOUS block".
    # I should use multi_replace_file_content.
    pass

# Switching strategy: Use multi_replace

    @classmethod
    def process_message(cls, text: str, user_id: int = None, agencia = None) -> str:
        """
        Main entry point. Receives text, returns a response string.
        Args:
            text: Message text
            user_id: Django User ID (optional)
            agencia: Agency instance (optional but recommended for SaaS)
        """
        if not text:
            return "🤔 No entendí eso."

        # 1. Intent Classification (Hybrid: Regex/Keyword First, then AI)
        intent = cls._classify_intent_hybrid(text)
        logger.info(f"Linkeo Intent Detected: {intent} for text: '{text}' (Agencia: {agencia})")

        # 2. Execution
        if intent == 'QUERY_SALES':
            return cls._handle_sales_query(text, agencia)
        elif intent == 'CHECK_TICKET':
            return cls._handle_ticket_query(text, agencia)
        elif intent == 'GENERAL':
            return cls._handle_general_chat(text)
        else:
            # Fallback to AI Chat if keywords fail
            return cls._handle_ai_chat(text, agencia)

    @classmethod
    def _classify_intent_hybrid(cls, text: str) -> str:
        """
        Simple keyword matching to save API tokens for common tasks.
        """
        text_lower = text.lower()
        
        # Sales Keywords
        if any(k in text_lower for k in ['venta', 'vendí', 'vendido', 'cierre', 'facturado']):
            return 'QUERY_SALES'
        
        # Ticket Keywords (Detect PNR or Ticket Number patterns)
        if any(k in text_lower for k in ['boleto', 'ticket', 'pnr', 'reserva']) or cls._extract_pnr(text):
            return 'CHECK_TICKET'
            
        # Greetings
        if any(k in text_lower for k in ['hola', 'buenos dias', 'buenas', 'gracias']):
            return 'GENERAL'
            
        return 'AI_CHAT' # Let Gemini handle it

    @classmethod
    def _handle_sales_query(cls, text: str, agencia=None) -> str:
        """
        Calculates sales for Today/Yesterday/Month.
        """
        if not agencia:
            return "⚠️ Error: No se ha identificado tu agencia. Contacta a soporte."
        now = timezone.now()
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Simple date logic (can be enhanced with AI later)
        periodo = "hoy"
        if "ayer" in text.lower():
            start_date = start_date - datetime.timedelta(days=1)
            end_date = start_date + datetime.timedelta(days=1)
            ventas = Venta.objects.filter(agencia=agencia, fecha_venta__range=(start_date, end_date))
            periodo = "ayer"
        elif "mes" in text.lower():
            start_date = start_date.replace(day=1)
            ventas = Venta.objects.filter(agencia=agencia, fecha_venta__gte=start_date)
            periodo = "este mes"
        else:
            # Default Today
            ventas = Venta.objects.filter(agencia=agencia, fecha_venta__gte=start_date)

        total_usd = sum(v.total_venta for v in ventas if v.moneda and v.moneda.codigo_iso == 'USD')
        total_ves = sum(v.total_venta for v in ventas if v.moneda and v.moneda.codigo_iso == 'VES')
        count = ventas.count()

        return (
            f"📊 <b>Reporte de Ventas ({periodo.capitalize()})</b>\n\n"
            f"🔢 Transacciones: {count}\n"
            f"💵 Total USD: ${total_usd:,.2f}\n"
            f"🇻🇪 Total VES: Bs {total_ves:,.2f}\n\n"
            f"<i>Linkeo AI</i> 🤖"
        )
    
    @classmethod
    def _handle_ticket_query(cls, text: str, agencia=None) -> str:
        if not agencia:
            return "⚠️ Error: No se ha identificado tu agencia."

        # Extract ID, PNR or Ticket Number
        import re
        # Try to find a numeric ticket ID (simple integer)
        id_match = re.search(r'\b(\d{1,5})\b', text)
        pnr_match = re.search(r'\b([A-Z0-9]{6})\b', text.upper())
        
        ticket = None
        if id_match:
            try:
                ticket = BoletoImportado.objects.get(pk=id_match.group(1), agencia=agencia)
            except BoletoImportado.DoesNotExist:
                pass
        
        if not ticket and pnr_match:
            ticket = BoletoImportado.objects.filter(localizador_pnr=pnr_match.group(1), agencia=agencia).last()

        if ticket:
            estado = ticket.get_estado_parseo_display()
            return (
                f"🎫 <b>Info Boleto #{ticket.pk}</b>\n"
                f"👤 Pasajero: {ticket.nombre_pasajero_completo or 'N/A'}\n"
                f"✈️ PNR: {ticket.localizador_pnr}\n"
                f"ℹ️ Estado: {estado}\n"
                f"📎 Archivo: {ticket.archivo_boleto.name}"
            )
        else:
            return "🔍 No encontré ningún boleto con esa información. Intenta enviarme el ID o PNR."

    @classmethod
    def _handle_general_chat(cls, text: str) -> str:
        return "¡Hola! Soy Linkeo 🤖. Puedo ayudarte consultando tus ventas o el estatus de tus boletos."

    @classmethod
    def _handle_ai_chat(cls, text: str, agencia=None) -> str:
        """
        Uses Gemini for open-ended queries fallback.
        Inyecta conocimiento de la Wiki (GDS Guides) si es relevante.
        """
        model = cls._get_gemini_model()
        if not model:
            return "Lo siento, mi cerebro de IA no está conectado (Falta API Key)."
        
        try:
            # 1. Buscar contexto relevante en la Wiki
            from core.models.wiki import WikiArticulo
            from django.db.models import Q
            
            contexto_wiki = ""
            keywords = text.upper().split()
            
            # Busqueda simple por coincidencia en tags o titulo
            # Ej: Si usuario dice "comando KIU", buscamos Wiki con tag KIU
            articulos = WikiArticulo.objects.filter(
                Q(tags__overlap=keywords) |  # Postgres only usually, but let's try generic fallback
                Q(titulo__icontains=keywords[0]) # Fallback simple
            ).filter(activo=True)[:2] 
            
            # Fallback para SQLite/Others si overlap falla o si la lista keywords es compleja
            # Hacemos una búsqueda iterativa segura
            relevant_articles = []
            for art in WikiArticulo.objects.filter(activo=True):
                # Check si algún tag del artículo está en el texto del usuario
                # Ej: Tag 'KIU' está en "Como cotizo en KIU?"
                if any(tag.upper() in text.upper() for tag in art.tags):
                   relevant_articles.append(art)
            
            if relevant_articles:
                contexto_wiki += "\n\n📚 **INFORMACIÓN INTERNA (Base de Conocimiento):**\n"
                for art in relevant_articles[:2]: # Max 2 articulos para no saturar token limit
                    contexto_wiki += f"--- {art.titulo} ---\n{art.contenido[:2000]}\n" # Truncar a 2000 chars por si acaso
            
            # 2. Construir Prompt
            prompt = f"""
            Eres Linkeo, el asistente experto de TravelHub.
            Tu misión es ayudar a agentes de viaje con comandos GDS, ventas y dudas generales.
            
            INFORMACIÓN DE CONTEXTO (Usa esto para responder si es relevante):
            {contexto_wiki}
            
            PREGUNTA DEL USUARIO:
            "{text}"
            
            INSTRUCCIONES:
            - Responde de forma concisa y profesional.
            - Si la respuesta está en la INFORMACIÓN DE CONTEXTO, úsala y cita el comando exacto.
            - Si es sobre GDS (Amadeus, Sabre, KIU), da el ejemplo de formato.
            - Si no sabes, dilo amablemente.
            """
            
            # 3. Generar
            response = model.generate_content(prompt)
            return response.text
            
        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "quota" in error_str.lower() or "ResourceExhausted" in error_str:
                logger.warning(f"Gemini Ration Limit Reached: {e}")
                return "⏳ Mi cerebro está un poco saturado (Límite de cuota alcanzado). Por favor espera 30 segundos y pregúntame de nuevo."
            
            logger.error(f"Gemini Error processing '{text}': {e}", exc_info=True)
            return f"😓 Tuve un error de conexión con mi cerebro artificial. ({str(e)})"

    @staticmethod
    def _extract_pnr(text):
        import re
        return re.search(r'\b[A-Z0-9]{6}\b', text)

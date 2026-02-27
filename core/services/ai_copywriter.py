import os
import logging
import google.generativeai as genai
from django.conf import settings
from core.models.tarifario_hoteles import HotelTarifario

logger = logging.getLogger(__name__)

class AICopywriter:
    """
    Generador de Copywriting para redes sociales usando Gemini 2.0 Flash.
    """
    
    def __init__(self):
        api_key = os.getenv('GEMINI_API_KEY') or getattr(settings, 'GEMINI_API_KEY', None)
        if not api_key:
            logger.error("GEMINI_API_KEY no encontrada.")
            self.model = None
            return

        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash')

    def generate_caption(self, hotel_id, tone="AVENTURERO"):
        """
        Genera un caption para Instagram basado en la info del hotel.
        """
        if not self.model:
            return "Error: IA no configurada."

        try:
            hotel = HotelTarifario.objects.get(pk=hotel_id)
        except HotelTarifario.DoesNotExist:
            return "Error: Hotel no encontrado."

        # Construir contexto
        amenities = [a.nombre for a in hotel.amenidades.all()]
        amenities_str = ", ".join(amenities)
        
        prompt = f"""
        Actúa como un experto Community Manager de viajes.
        Escribe un POST DE INSTAGRAM atractivo para vender este hotel.
        
        HOTEL: {hotel.nombre}
        DESTINO: {hotel.destino}
        CATEGORÍA: {hotel.categoria} Estrellas
        AMENIDADES: {amenities_str}
        DESCRIPCIÓN: {hotel.descripcion_larga[:300]}...
        
        TONO SOLICITADO: {tone}
        (Opciones: FORMAL, AVENTURERO, ROMÁNTICO, FAMILIAR)
        
        REQUISITOS:
        1. Empieza con un Hook (Gancho) emocional.
        2. Usa emojis relevantes.
        3. Invita a la acción (CTA) para reservar en la Agencia.
        4. Incluye 5-8 hashtags relevantes (#TravelHub #Venezuela, etc).
        5. NO uses comillas al principio ni al final. Solo el texto.
        """
        
        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            logger.error(f"Error generando copy: {e}")
            return "Hubo un error generando el texto. Intenta de nuevo."

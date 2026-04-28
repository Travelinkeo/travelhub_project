import os
import logging
from core.models.tarifario_hoteles import HotelTarifario
from core.services.ai_engine import ai_engine

logger = logging.getLogger(__name__)

class AICopywriter:
    """
    Generador de Copywriting para redes sociales usando Gemini 2.0 Flash.
    """
    
    def __init__(self):
        pass

    def generate_caption(self, hotel_id, tone="PROFESIONAL_AVENTURERO"):
        """
        Genera un caption para Instagram basado en la info del hotel.
        """
        if not ai_engine.is_ready:
            return "IA no disponible (revisa config)."

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
        (Opciones: PROFESIONAL_AVENTURERO (Mezcla profesional/aventura), FORMAL, AVENTURERO, ROMÁNTICO)
        
        REQUISITOS:
        1. Empieza con un Hook (Gancho) emocional.
        2. Usa emojis relevantes.
        3. Invita a la acción (CTA) para reservar en la Agencia.
        4. Incluye 5-8 hashtags relevantes (#TravelHub #Venezuela, etc).
        5. NO uses comillas al principio ni al final. Solo el texto.
        """
        
        try:
            response = ai_engine.call_gemini(prompt)
            return response.get("text", "Sin respuesta").strip()
        except Exception as e:
            logger.error(f"Error generando copy: {e}")
            return "Hubo un error generando el texto. Intenta de nuevo."

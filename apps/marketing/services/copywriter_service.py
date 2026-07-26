import logging
from typing import Any

from pydantic import BaseModel, Field


def _get_ai_engine():
    """_get_ai_engine."""
    from django.utils.module_loading import import_string

    return import_string("apps.automation.services.ai_engine.ai_engine")


def _get_hotel_tarifario_model():
    """_get_hotel_tarifario_model."""
    from django.apps import apps

    return apps.get_model("bookings", "HotelTarifario")


logger = logging.getLogger(__name__)


class CaptionVariant(BaseModel):
    """CaptionVariant."""

    tone_name: str = Field(description="Nombre del tono (Ej: Emocional, Enganchador, Minimalista)")
    text: str = Field(description="El texto del caption")


class SocialMediaPackage(BaseModel):
    """SocialMediaPackage."""

    variants: list[CaptionVariant] = Field(description="3 variaciones del caption")
    hashtags: list[str] = Field(description="Lista de hashtags optimizados para alcance")
    best_time_to_post: str = Field(description="Recomendación de horario (Ej: Hoy, 6:30 PM)")
    engagement_prediction: str = Field(description="Predicción de engagement (Ej: +14%)")


class CopywriterService:
    """
    Generador de Copywriting para redes sociales usando Gemini 2.0 Flash.
    """

    def __init__(self):
        """__init__."""
        pass

    def generate_caption(self, hotel_id, tone="PROFESIONAL_AVENTURERO"):
        """
        Genera un caption para Instagram basado en la info del hotel.
        """
        ai_engine = _get_ai_engine()
        if not ai_engine.is_ready:
            return "IA no disponible (revisa config)."

        try:
            HotelTarifario = _get_hotel_tarifario_model()
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
        (Opciones: PROFESIONAL_AVENTURERO (Mesa entre ambos), FORMAL, AVENTURERO, ROMÁNTICO)

        REQUISITOS:
        1. Empieza con un Hook (Gancho) emocional.
        2. Usa emojis relevantes.
        3. Invita a la acción (CTA) para reservar en la Agencia.
        4. Incluye 5-8 hashtags relevantes (#TravelHub #Venezuela, etc).
        5. NO uses comillas al principio ni al final. Solo el texto.
        """

        try:
            response = _get_ai_engine().call_gemini(prompt)
            return response.get("text", "Sin respuesta").strip()
        except Exception as e:
            logger.error(f"Error generando copy: {e}")
            return "Hubo un error generando el texto. Intenta de nuevo."

    def generate_social_package(self, hotel_id, tone="LUXURY", extra_prompt=None) -> dict[str, Any]:
        """
        Genera un paquete completo (variantes, hashtags, horario) usando salida estructurada.
        """
        ai_engine = _get_ai_engine()
        if not ai_engine.is_ready:
            return {"error": "IA no disponible"}

        try:
            HotelTarifario = _get_hotel_tarifario_model()
            hotel = HotelTarifario.objects.get(pk=hotel_id)
        except HotelTarifario.DoesNotExist:
            return {"error": "Hotel no encontrado"}

        amenities = [a.nombre for a in hotel.amenidades.all()]

        # Mapeo de tonos para mayor claridad en el prompt
        tone_context = {
            "LUXURY": "enfoque en exclusividad, materiales premium, servicio de guante blanco y elegancia.",
            "ADVENTURE": "enfoque en exploración, adrenalina, contacto con la naturaleza salvaje y autenticidad.",
            "MINIMAL": "texto directo, limpio, con mucho espacio visual y elegancia austera.",
            "VIBRANT": "lleno de energía, colores, vida nocturna, actividades y entusiasmo contagioso.",
        }

        selected_tone_desc = tone_context.get(tone, "un equilibrio profesional y sugerente.")

        prompt = f"""
        Genera un paquete de contenido de ALTA GAMA para Instagram para el hotel: {hotel.nombre}.
        Ubicación: {hotel.destino}.
        Categoría: {hotel.categoria} estrellas.
        Descripción base: {hotel.descripcion_larga[:400]}
        Amenidades clave: {", ".join(amenities)}

        ESTILO VISUAL Y VOZ: {selected_tone_desc}

        {"INSTRUCCIÓN ADICIONAL DEL USUARIO: " + extra_prompt if extra_prompt else ""}

        REQUISITOS ESTRATÉGICOS:
        1. Variantes:
           - Variante 1 (EMOCIONAL): Conecta con los deseos profundos del viajero.
           - Variante 2 (ENGANCHADOR): Usa un 'hook' potente y una pregunta al final.
           - Variante 3 (MINIMALISTA): Máximo 2 líneas de texto puro impacto.
        2. Hashtags: Mezcla de hashtags de nicho (50k-100k posts) y generales (1M+ posts) para optimizar alcance.
        3. Cronograma: Recomienda un horario basado en picos de audiencia de viajes.
        4. No uses placeholders como [Nombre], usa la información real del hotel.
        """

        try:
            package = _get_ai_engine().call_gemini(
                prompt=prompt, response_schema=SocialMediaPackage
            )
            return package
        except Exception as e:
            logger.error(f"Error generando paquete social: {e}")
            return {"error": str(e)}

import os
import logging
# import google.generativeai as genai
from django.conf import settings
from apps.cms.models import Articulo, GuiaDestino, PostRedesSociales
from django.utils.text import slugify
from django.utils import timezone

logger = logging.getLogger(__name__)

class CMSContentService:
    """
    Servicio para automatizar la creación de contenido de marketing
    utilizando Gemini 2.0 Flash.
    """

    def __init__(self):
        self.api_key = os.environ.get("GEMINI_API_KEY") or getattr(settings, "GEMINI_API_KEY", None)
        if self.api_key:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key, transport="rest")
            self.model = genai.GenerativeModel("gemini-2.0-flash")

    def generate_social_post(self, context_data: str, plataforma: str = "Instagram") -> dict:
        """
        Genera un copy para redes sociales basado en datos de contexto (ej: un itinerario).
        """
        prompt = f"""
        Actúa como un experto en Marketing Turístico. Genera un post atractivo para {plataforma}.
        Contexto del viaje/promoción: {context_data}
        
        Requisitos:
        1. Tono sugerente, profesional y aventurero.
        2. Incluye emojis relevantes.
        3. Incluye una lista de 5-10 hashtags optimizados.
        4. No uses placeholders como [Nombre de la Agencia], usa 'TravelHub'.
        
        Retorna el resultado en formato JSON con las llaves: 'caption' y 'hashtags'.
        """
        
        try:
            response = self.model.generate_content(
                prompt,
                generation_config={"response_mime_type": "application/json"}
            )
            return response.text
        except Exception as e:
            logger.exception("Error generando post social")
            return {"error": str(e)}

    def generate_destination_guide_data(self, nombre_destino: str) -> dict:
        """
        Genera información técnica y descriptiva para una guía de destino.
        """
        prompt = f"""
        Investiga y genera una guía de destino para: {nombre_destino}.
        Escribe en Español.
        
        Campos requeridos:
        - descripcion: Un párrafo inspirador de unas 100 palabras.
        - mejor_epoca: Cuándo viajar y por qué.
        - requisitos_visa: Información general para ciudadanos de Latinoamérica.
        - moneda_local: Nombre y código de la moneda.
        - idioma: Idiomas oficiales y hablados.
        
        Retorna en formato JSON.
        """
        
        try:
            response = self.model.generate_content(
                prompt,
                generation_config={"response_mime_type": "application/json"}
            )
            return response.text
        except Exception as e:
            logger.exception("Error generando guía de destino")
            return {"error": str(e)}

    def generate_blog_article(self, tema: str, destino: str = "") -> Articulo:
        """
        Crea un objeto Articulo completo con contenido generado por IA.
        """
        prompt = f"""
        Escribe un artículo de blog SEO-friendly sobre: {tema}. 
        Destino relacionado: {destino}.
        Formato: Markdown.
        
        Estructura:
        1. Título llamativo.
        2. Resumen corto para meta-description.
        3. Contenido extenso con subtítulos (H2, H3).
        4. Tono: Informativo y persuasivo.
        
        Retorna en formato JSON con llaves: 'titulo', 'resumen', 'contenido', 'meta_titulo', 'meta_descripcion'.
        """
        
        try:
            response = self.model.generate_content(
                prompt,
                generation_config={"response_mime_type": "application/json"}
            )
            import json
            data = json.loads(response.text)
            
            # Robustez: Gemini a veces retorna una lista de un objeto
            if isinstance(data, list) and len(data) > 0:
                data = data[0]
            
            articulo = Articulo(
                titulo=data.get('titulo', tema),
                slug=slugify(data.get('titulo', tema)),
                resumen=data.get('resumen', ''),
                contenido=data.get('contenido', ''),
                meta_titulo=data.get('meta_titulo', ''),
                meta_descripcion=data.get('meta_descripcion', ''),
                destino=destino,
                generado_por_ia=True,
                prompt_ia=prompt,
                estado=Articulo.EstadoArticulo.BORRADOR
            )
            return articulo
        except Exception as e:
            logger.exception("Error creando artículo de blog")
            raise e

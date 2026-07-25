"""Servicio de content service para la aplicación cms.
"""

import json
import logging

from django.utils.text import slugify

from ..models import Articulo, PostRedesSociales

logger = logging.getLogger(__name__)


def _get_genai():
    # _get_genai:  get genai. Args: según implementación. Returns: según implementación.
    from google import genai

    return genai


class AIContentService:
    """
    Servicio para generar contenido de viajes (artículos, guías, posts) usando Gemini.
    """

    def __init__(self):
        # __init__: Inicializa una nueva instancia de AIContentService. Args: parámetros de inicialización.
        from django.conf import settings

        genai = _get_genai()
        api_key = getattr(settings, "GEMINI_API_KEY", None)
        self.client = genai.Client(api_key=api_key)
        self.model_name = "gemini-2.5-flash"

    def generate_article(self, destination, keywords=None):
        """
        Genera un artículo completo de blog sobre un destino.
        """
        prompt = f"""
        Actúa como un redactor experto en viajes para una agencia de turismo de lujo llamada Travelinkeo.
        Escribe un artículo de blog SEO-optimizado sobre el destino: {destination}.
        Palabras clave sugeridas: {keywords if keywords else destination}

        El artículo debe incluir:
        1. Título llamativo.
        2. Resumen corto.
        3. 3-4 secciones con subtítulos (Markdown).
        4. Meta-título y Meta-descripción para SEO.

        Responde ÚNICAMENTE en formato JSON con la siguiente estructura:
        {{
            "titulo": "...",
            "resumen": "...",
            "contenido": "...",
            "meta_titulo": "...",
            "meta_descripcion": "..."
        }}
        """

        try:
            response = self.client.models.generate_content(model=self.model_name, contents=prompt)
            # Limpiar la respuesta si tiene bloques de markdown
            content = response.text.strip()
            if content.startswith("```json"):
                content = content[7:-3].strip()

            data = json.loads(content)

            # Crear el artículo en la DB
            articulo = Articulo.objects.create(
                titulo=data["titulo"],
                slug=slugify(data["titulo"]),
                resumen=data["resumen"],
                contenido=data["contenido"],
                destino=destination,
                generado_por_ia=True,
                prompt_ia=prompt,
                meta_titulo=data["meta_titulo"],
                meta_descripcion=data["meta_descripcion"],
            )

            return articulo

        except Exception as e:
            logger.error(f"Error generando artículo para {destination}: {e}")
            raise

    def generate_social_posts(self, articulo_id):
        """
        Genera fragmentos para redes sociales basados en un artículo.
        """
        articulo = Articulo.objects.get(id=articulo_id)

        prompt = f"""
        Basado en el siguiente artículo sobre {articulo.destino}:
        '{articulo.resumen}'

        Genera posts cortos para: Instagram, Telegram y LinkedIn.
        Incluye emojis y hashtags relevantes.

        Responde ÚNICAMENTE en JSON:
        {{
            "INSTAGRAM": "caption...",
            "TELEGRAM": "mensaje...",
            "LINKEDIN": "post profesional...",
            "hashtags": "#travel #lux..."
        }}
        """

        try:
            response = self.client.models.generate_content(model=self.model_name, contents=prompt)
            content = response.text.strip()
            if content.startswith("```json"):
                content = content[7:-3].strip()

            data = json.loads(content)
            hashtags = data.pop("hashtags", "")

            posts = []
            # Mapeo de plataforma
            mapping = {
                "INSTAGRAM": PostRedesSociales.Plataforma.INSTAGRAM,
                "TELEGRAM": PostRedesSociales.Plataforma.TELEGRAM,
                "LINKEDIN": PostRedesSociales.Plataforma.LINKEDIN,
            }

            for key, plat in mapping.items():
                if key in data:
                    post = PostRedesSociales.objects.create(
                        articulo=articulo, plataforma=plat, contenido=data[key], hashtags=hashtags
                    )
                    posts.append(post)

            return posts

        except Exception as e:
            logger.error(f"Error generando posts para artículo {articulo_id}: {e}")
            raise

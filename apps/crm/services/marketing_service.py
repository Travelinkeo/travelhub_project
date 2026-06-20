import logging
from datetime import timedelta

from django.db.models import Max, Q
from django.utils import timezone
from pydantic import BaseModel, Field

from apps.crm.models import Cliente


def _get_ai_engine():
    from django.utils.module_loading import import_string

    return import_string("apps.automation.services.ai_engine.ai_engine")


logger = logging.getLogger(__name__)


# ─── MODO 1: CAMPAÑA A CLIENTES ────────────────────────────────────────────────
class CampanaMarketingSchema(BaseModel):
    destinos_clave: list[str] = Field(
        description="Ciudades o países mencionados (ej. ['MADRID', 'EUROPA']). Vacío si no aplica."
    )
    meses_inactividad: int = Field(
        default=0, description="Meses sin comprar mencionados (ej. 12 si dice 'hace un año')."
    )
    asunto_email: str = Field(
        description="Asunto atractivo y persuasivo para el correo (máx 50 chars)."
    )
    cuerpo_email_html: str = Field(
        description="Cuerpo del correo en HTML estilizado y moderno. DEBE incluir la variable {{ nombre_cliente }} para personalizar el saludo."
    )


SYSTEM_PROMPT_CAMPANA = """
Eres el Director de Marketing IA de TravelHub, una agencia de viajes premium.
Tu tarea es analizar la solicitud del agente, extraer los parámetros de búsqueda de clientes (destinos y tiempo de inactividad) y redactar un correo electrónico de alta conversión (HTML).
Usa tonos cálidos, emojis moderados y un estilo "Boutique".
MUY IMPORTANTE: Usa la variable exacta {{ nombre_cliente }} donde deba ir el nombre del pasajero.
"""


# ─── MODO 2: CONTENIDO CREATIVO (BRANDING / COPY / SOCIAL) ─────────────────────
class ContenidoCreativoSchema(BaseModel):
    tipo_contenido: str = Field(
        description="Tipo de contenido: 'branding', 'post_instagram', 'post_facebook', 'slogan', 'copy_web', 'email_generico', 'guion_video', 'descripcion_destino', 'otro'."
    )
    titulo: str = Field(description="Título o encabezado principal del contenido generado.")
    contenido_principal: str = Field(
        description="El contenido completo generado en HTML. Puede incluir texto, listas, etiquetas de imagen sugeridas, hashtags, etc."
    )
    sugerencias_visuales: list[str] = Field(
        default=[],
        description="Lista de sugerencias visuales: paleta de colores, tipo de imágenes recomendadas, estilo fotográfico.",
    )
    keywords_visuales: list[str] = Field(
        default=[],
        description="3 o 4 palabras clave en INGLÉS para buscar imágenes en Unsplash (ej: ['madrid', 'luxury', 'skyline']).",
    )
    hashtags: list[str] = Field(
        default=[], description="Hashtags relevantes si aplica (ej. para Instagram/Facebook)."
    )


SYSTEM_PROMPT_CREATIVO = """
Eres el Director Creativo IA de TravelHub, una agencia de viajes boutique premium.
Tu tarea es generar contenido creativo de alta calidad: branding, copies para redes sociales, slogans, textos web, guiones o descripciones de destinos.
El contenido debe ser moderno, aspiracional, usar el tono de una agencia de viajes de lujo y puede incluir emojis donde corresponda.
Genera el contenido en HTML listo para mostrar, con etiquetas <h2>, <p>, <ul>, <strong>, etc.
Si el usuario pide algo específico de un destino o sitio web, hazlo centrado en eso.
"""


# ─── CLASIFICADOR: ¿Es campaña o contenido creativo? ───────────────────────────
class ClasificadorSchema(BaseModel):
    modo: str = Field(
        description="'campana' si el usuario quiere enviar correos a clientes específicos de la base de datos. 'creativo' si quiere generar branding, copy, posts, slogans, textos web u otro contenido creativo sin buscar clientes."
    )
    razon: str = Field(description="Breve explicación del por qué elegiste ese modo.")


SYSTEM_PROMPT_CLASIFICADOR = """
Eres un clasificador de intenciones de marketing.
Dado el texto del usuario, debes determinar si quiere:
- 'campana': Buscar clientes en una base de datos y enviarles correos personalizados.
- 'creativo': Generar contenido creativo (branding, posts, slogans, copy para un sitio web, descripción de un destino, etc.) SIN necesitar datos de clientes.
Analiza el texto y responde con precisión.
"""


class MarketingAIEngine:
    @staticmethod
    def _clasificar_intencion(prompt: str) -> str:
        """Retorna 'campana' o 'creativo' según el prompt del usuario."""
        try:
            resultado = _get_ai_engine().parse_structured_data(
                text=prompt, schema=ClasificadorSchema, system_prompt=SYSTEM_PROMPT_CLASIFICADOR
            )
            if resultado:
                tipo_resultado = type(resultado).__name__
                model_dump_fn = getattr(resultado, "model_dump", None)
                if callable(model_dump_fn):
                    data = model_dump_fn()
                elif isinstance(resultado, dict):
                    data = resultado
                else:
                    logger.error(
                        f"[MarketingAIEngine] Tipo inesperado: {tipo_resultado} - {resultado}"
                    )
                    data = getattr(resultado, "dict", lambda: resultado)()
                return data.get("modo", "creativo")
        except Exception as e:
            logger.warning(f"Clasificador falló, usando modo creativo por defecto: {e}")
        return "creativo"

    @staticmethod
    def generar_contenido_creativo(prompt_agente: str, formato_imagen: str = "portrait") -> dict:
        """Genera branding, copy, posts o cualquier contenido creativo sin clientes."""
        try:
            logger.info(
                f"🎨 Generando contenido creativo: {prompt_agente} (Formato: {formato_imagen})"
            )

            resultado_ia = _get_ai_engine().parse_structured_data(
                text=prompt_agente,
                schema=ContenidoCreativoSchema,
                system_prompt=SYSTEM_PROMPT_CREATIVO,
            )

            if not resultado_ia:
                raise ValueError("La IA no pudo generar contenido.")

            model_dump_fn = getattr(resultado_ia, "model_dump", None)
            if callable(model_dump_fn):
                data = model_dump_fn()
            elif isinstance(resultado_ia, dict):
                data = resultado_ia
            else:
                data = resultado_ia.dict()

            # Limpiar markdown residual
            for campo in ["contenido_principal", "titulo"]:
                if campo in data and data[campo]:
                    data[campo] = data[campo].replace("```html", "").replace("```", "").strip()

            # 📸 BUSCAR IMÁGENES REALES PARA EL MOODBOARD
            imágenes_reales = []
            keywords = data.get("keywords_visuales", [])

            # Map user selected size format to unsplash parameters
            unsplash_orientation = "portrait"
            medidas_recomendadas = "1080 × 1350 px (Proporción 4:5)"
            advertencia_formato = ""

            if formato_imagen == "squarish":
                unsplash_orientation = "squarish"
                medidas_recomendadas = "1080 × 1080 px (Proporción 1:1) - Cuadrado"
            elif formato_imagen == "landscape":
                unsplash_orientation = "landscape"
                medidas_recomendadas = "1080 × 566 px (Proporción 1.91:1) - Horizontal"
            elif formato_imagen == "stories":
                unsplash_orientation = "portrait"
                medidas_recomendadas = "1080 × 1920 px (Proporción 9:16) - Reels/Stories"
                advertencia_formato = "Para Reels y Stories: evita poner textos importantes en la esquina inferior izquierda y bordes extremos para evitar cortes en el feed."
            else:  # default 'portrait'
                unsplash_orientation = "portrait"
                medidas_recomendadas = "1080 × 1350 px (Proporción 4:5) o 1080 × 1440 px (Proporción 3:4) - Vertical Feed"

            data["formato_recomendado"] = medidas_recomendadas
            data["advertencia_formato"] = advertencia_formato

            if keywords:
                import os

                from django.conf import settings

                unsplash_key = os.environ.get("UNSPLASH_ACCESS_KEY") or getattr(
                    settings, "UNSPLASH_ACCESS_KEY", ""
                )
                if unsplash_key:
                    import requests

                    clean_key = str(unsplash_key).strip("'\"")
                    # Para evitar búsquedas vacías por conjunción de demasiados términos,
                    # buscamos cada keyword de forma individual hasta completar máximo 4 imágenes.
                    for kw in keywords[:4]:
                        if len(imágenes_reales) >= 4:
                            break
                        try:
                            url = "https://api.unsplash.com/search/photos"
                            # Si es la única keyword pedimos 4, si son 2 pedimos 2, de lo contrario 1 o 2 por keyword
                            per_page = max(1, 4 // len(keywords))
                            params = {
                                "query": kw,
                                "client_id": clean_key,
                                "per_page": per_page,
                                "orientation": unsplash_orientation,
                            }
                            response = requests.get(url, params=params, timeout=5)
                            if response.status_code == 200:
                                results = response.json().get("results", [])
                                for img in results:
                                    if len(imágenes_reales) < 4:
                                        imágenes_reales.append(
                                            {
                                                "url": img.get("urls", {}).get("regular"),
                                                "alt": img.get("alt_description")
                                                or "Inspiración de viaje",
                                            }
                                        )
                        except Exception as e_unsplash:
                            logger.warning(f"Error consultando Unsplash para '{kw}': {e_unsplash}")

            data["imagenes_inspiracion"] = imágenes_reales[:4]  # Tomar las 4 mejores

            return {"modo": "creativo", "contenido": data}

        except Exception as e:
            logger.error(f"Error en generar_contenido_creativo: {e}")
            return {"error": str(e)}

    @staticmethod
    def generar_campana(prompt_agente: str) -> dict:
        """Genera una campaña de correo segmentada a clientes de la BD."""
        try:
            logger.info(f"📧 Procesando campaña de clientes: {prompt_agente}")

            resultado_ia = _get_ai_engine().parse_structured_data(
                text=prompt_agente,
                schema=CampanaMarketingSchema,
                system_prompt=SYSTEM_PROMPT_CAMPANA,
            )

            if not resultado_ia:
                raise ValueError("La IA no pudo procesar la campaña.")

            if hasattr(resultado_ia, "model_dump"):
                data = resultado_ia.model_dump()
            elif isinstance(resultado_ia, dict):
                data = resultado_ia
            else:
                data = resultado_ia.dict()

            # Limpieza de posible Markdown de Gemini en el HTML
            if "cuerpo_email_html" in data:
                data["cuerpo_email_html"] = (
                    data["cuerpo_email_html"].replace("```html", "").replace("```", "").strip()
                )

            # Normalización de llaves
            data = {
                ("".join(["_" + c.lower() if c.isupper() else c for c in k]).lstrip("_")): v
                for k, v in data.items()
            }

            meses = data.get("meses_inactividad", 0)
            destinos = data.get("destinos_clave", [])

            # Fallbacks
            if not data.get("asunto_email"):
                data["asunto_email"] = "¡Preparamos algo especial para tu próximo viaje! ✈️"
            if not data.get("cuerpo_email_html"):
                data["cuerpo_email_html"] = (
                    f"<h2>Hola {{{{ nombre_cliente }}}},</h2><p>Tenemos ofertas especiales basadas en tus viajes previos a {', '.join(destinos) if destinos else 'tus destinos favoritos'}. ¡Contáctanos!</p>"
                )

            clientes_query = Cliente.objects.annotate(
                ultima_compra=Max("ventas_asociadas__fecha_venta")
            )

            if meses > 0:
                fecha_limite = timezone.now() - timedelta(days=30 * meses)
                clientes_query = clientes_query.filter(
                    Q(ultima_compra__lt=fecha_limite) | Q(ultima_compra__isnull=True)
                )

            if destinos:
                q_destinos = Q()
                for destino in destinos:
                    q_destinos |= Q(
                        ventas_asociadas__items_venta__descripcion_personalizada__icontains=destino
                    )
                    q_destinos |= Q(ventas_asociadas__descripcion_general__icontains=destino)
                clientes_query = clientes_query.filter(q_destinos).distinct()

            clientes_query = clientes_query.exclude(email__isnull=True).exclude(email__exact="")

            clientes_target_list = list(
                clientes_query.values("id", "nombres", "apellidos", "email")
            )
            cliente_ids = [c["id"] for c in clientes_target_list]

            return {
                "modo": "campana",
                "ia_data": data,
                "clientes_target": clientes_target_list,
                "cliente_ids": cliente_ids,
                "total_audiencia": clientes_query.count(),
            }

        except Exception as e:
            logger.error(f"Error en generar_campana: {e}")
            return {"error": str(e)}

    @staticmethod
    def procesar(prompt_agente: str, formato_imagen: str = "portrait") -> dict:
        """
        Punto de entrada unificado.
        Clasifica el prompt y delega al método adecuado:
        - 'campana': envio masivo a clientes
        - 'creativo': generación de branding/copy/social sin clientes
        """
        modo = MarketingAIEngine._clasificar_intencion(prompt_agente)
        logger.info(f"🎯 Modo detectado: {modo}")

        if modo == "campana":
            return MarketingAIEngine.generar_campana(prompt_agente)
        else:
            return MarketingAIEngine.generar_contenido_creativo(
                prompt_agente, formato_imagen=formato_imagen
            )

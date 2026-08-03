import io
import logging
from decimal import Decimal
from typing import Any

import requests
from django.core.files.storage import default_storage
from PIL import Image, ImageDraw, ImageFont

from core.api import Agencia

logger = logging.getLogger(__name__)


class MarketingService:
    """MarketingService."""

    @staticmethod
    def generate_instagram_story(hotel_id: int, agencia_id: int | None = None) -> io.BytesIO:
        """
        Generates a 1080x1920 JPG for Instagram Stories.
        """
        # 1. Fetch Data
        from django.apps import apps

        HotelTarifario = apps.get_model("bookings", "HotelTarifario")
        TarifaHabitacion = apps.get_model("bookings", "TarifaHabitacion")
        hotel = HotelTarifario.objects.get(pk=hotel_id)

        # Calculate "From" Price
        min_price = Decimal(0)

        # Find lowest DBL rate
        tarifas = TarifaHabitacion.objects.filter(
            tipo_habitacion__hotel=hotel,
            tipo_tarifa="POR_PERSONA",  # Assumed standard
        ).order_by("tarifa_dbl")

        if tarifas.exists():
            best_rate = tarifas.first()
            min_price = best_rate.tarifa_dbl

        # Agency Branding
        agencia = None
        if agencia_id:
            agencia = Agencia.objects.filter(pk=agencia_id).first()

        if not agencia:
            agencia = Agencia.objects.filter(activa=True).first()  # Fallback

        # 2. Canvas Setup (1080x1920)
        W, H = 1080, 1920
        canvas = Image.new("RGB", (W, H), (20, 20, 20))

        # 3. Load Main Image
        try:
            if hotel.imagen_principal:
                # Handle FileField (S3/Cloudinary or Local)
                try:
                    # Try opening directly if local
                    img_file = default_storage.open(hotel.imagen_principal.name)
                    bg_img = Image.open(img_file).convert("RGB")
                except Exception:
                    logger.debug(
                        "Local storage open falló para %s, intentando URL",
                        hotel.imagen_principal.name,
                    )
                    url = hotel.imagen_principal.url
                    resp = requests.get(url, stream=True, timeout=30)
                    bg_img = Image.open(resp.raw).convert("RGB")
            else:
                # Placeholder Gradient
                bg_img = Image.new("RGB", (W, H), (50, 50, 100))
        except Exception as e:
            logger.error(f"Error loading image: {e}")
            bg_img = Image.new("RGB", (W, H), (100, 50, 50))

        # 4. Aspect Fill Resize
        bg_w, bg_h = bg_img.size
        ratio = max(W / bg_w, H / bg_h)
        new_size = (int(bg_w * ratio), int(bg_h * ratio))
        bg_img = bg_img.resize(new_size, Image.Resampling.LANCZOS)

        # Crop Center
        left = (new_size[0] - W) / 2
        top = (new_size[1] - H) / 2
        bg_img = bg_img.crop((left, top, left + W, top + H))

        canvas.paste(bg_img, (0, 0))

        # 5. Gradient Overlay (Bottom)
        gradient = Image.new("L", (W, H), 0)
        draw_grad = ImageDraw.Draw(gradient)
        # Black gradient from 50% down
        for y in range(int(H * 0.4), H):
            alpha = int(255 * ((y - H * 0.4) / (H * 0.6)))
            draw_grad.line([(0, y), (W, y)], fill=alpha)

        overlay = Image.new("RGB", (W, H), (0, 0, 0))
        canvas.paste(overlay, (0, 0), mask=gradient)

        # 6. Typography
        draw = ImageDraw.Draw(canvas)

        # Fonts (Try to load system fonts or fallback)
        def load_font(size):
            """load_font."""
            try:
                # Windows standard path
                return ImageFont.truetype("arial.ttf", size)
            except Exception:
                logger.debug("Arial font not found, trying DejaVu")
                try:
                    return ImageFont.truetype(
                        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", size
                    )
                except Exception:
                    logger.debug("DejaVu font not found either, using PIL default")
                    return ImageFont.load_default()

        font_title = load_font(80)
        font_sub = load_font(40)
        font_price = load_font(70)

        # Helper Center Text
        def draw_text_center(y, text, font, color="white"):
            """draw_text_center."""
            # Text bounding box
            bbox = draw.textbbox((0, 0), text, font=font)
            text_w = bbox[2] - bbox[0]
            x = (W - text_w) / 2
            draw.text((x, y), text, font=font, fill=color)

        # Content - Bottom
        margin_bottom = 300

        # Hotel Name
        draw_text_center(H - margin_bottom - 100, hotel.nombre.upper(), font_title)

        # Destination & Stars
        stars = "⭐" * hotel.categoria
        draw_text_center(
            H - margin_bottom, f"{hotel.destino.upper()}  |  {stars}", font_sub, color="#fbbf24"
        )

        # Price Tag (Floating Top Right or Below name)
        if min_price > 0:
            price_text = f"Desde ${int(min_price)}"
            # Round pill background
            # bbox = draw.textbbox((0,0), price_text, font=font_price)
            # ... simple text for now
            draw_text_center(H - margin_bottom + 80, price_text, font_price, color="#4ade80")

        # Agency Branding (Top Center)
        if agencia and agencia.logo:
            try:
                if agencia.logo.name:  # Local check
                    try:
                        f_logo = default_storage.open(agencia.logo.name)
                        logo_img = Image.open(f_logo).convert("RGBA")
                    except Exception:
                        logger.debug(
                            "Local logo open falló para %s, intentando URL", agencia.logo.name
                        )
                        resp = requests.get(agencia.logo.url, stream=True, timeout=30)
                        logo_img = Image.open(resp.raw).convert("RGBA")

                    # Resize logo (max width 400, max height 200)
                    logo_img.thumbnail((400, 200), Image.Resampling.LANCZOS)
                    lw, lh = logo_img.size
                    x_logo = int((W - lw) / 2)
                    y_logo = 150
                    canvas.paste(logo_img, (x_logo, y_logo), logo_img)
            except Exception as e:
                logger.warning(f"Logo error: {e}")
                draw_text_center(100, agencia.nombre, font_sub)
        else:
            if agencia:
                draw_text_center(100, agencia.nombre, font_sub)

        # 7. Output
        output = io.BytesIO()
        canvas.save(output, format="JPEG", quality=95)
        output.seek(0)
        return output

    @staticmethod
    def generate_social_caption(
        nombre_producto: str, destino: str, detalles: str, tono: str = "AVENTURERO"
    ) -> str:
        """
        Generates an Instagram/Facebook caption using Gemini AI.
        Agrega hashtags y emojis.
        """
        from django.utils.module_loading import import_string

        generate_text_from_prompt = import_string(
            "apps.automation.services.ai_engine.generate_text_from_prompt"
        )

        prompt = f"""
        Actúa como un experto experto en Marketing Turístico y Redes Sociales.
        Escribe un CAPTION (Pie de foto) para Instagram para promocionar lo siguiente:

        PRODUCTO: {nombre_producto}
        DESTINO: {destino}
        DETALLES CLAVE: {detalles}

        TONO: {tono} (Opciones: Divertido, Lujoso, Urgente, Informativo)

        ESTRUCTURA:
        1. Hook/Gancho inicial (pregunta o afirmación fuerte).
        2. Cuerpo corto y persuasivo (beneficios).
        3. Llamada a la acción (CTA) clara (Reserva ya, Escríbenos).
        4. Bloque de 10 Hashtags optimizados para turismo en Venezuela/Latam.

        Usa emojis estratégicamente. No uses comillas envolviendo el texto.
        """

        return generate_text_from_prompt(prompt)

    @staticmethod
    def generate_email_newsletter(ofertas: list[dict[str, Any]]) -> str:
        """
        Generates an HTML Newsletter Summary for a list of deals.
        ofertas: List of dicts or objects with 'titulo', 'precio', 'destino'.
        """
        from django.utils.module_loading import import_string

        generate_text_from_prompt = import_string(
            "apps.automation.services.ai_engine.generate_text_from_prompt"
        )

        lista_ofertas = ""
        for i, oferta in enumerate(ofertas, 1):
            # Manejo flexible de objetos o dicts
            titulo = (
                oferta.get("titulo")
                if isinstance(oferta, dict)
                else getattr(oferta, "titulo", "Oferta")
            )
            precio = (
                oferta.get("precio")
                if isinstance(oferta, dict)
                else getattr(oferta, "precio", "Consultar")
            )
            lista_ofertas += f"{i}. {titulo} - Desde {precio}\n"

        prompt = f"""
        Eres un Copywriter de Email Marketing experto en turismo.
        Genera el CONTENIDO HTML (solo el <body> interno, sin tags html/head externos)
        para un Newsletter semanal de ofertas de viaje.

        OFERTAS A INCLUIR:
        {lista_ofertas}

        REQUISITOS:
        - Usa un tono entusiasta y profesional.
        - Estructura HTML limpia con estilos inline básicos (CSS) para que se vea bien en Gmail.
        - Incluye un saludo personalizado (placeholder {{ nombre }}).
        - Una breve intro sobre "Escápate de la rutina".
        - Lista las ofertas con un diseño atractivo (tarjetas o lista bullet points estilizada).
        - Un botón CTA final "Ver todas las ofertas".
        - Despedida de "El equipo de TravelHub".

        Output esperado: Solo código HTML.
        """

        return generate_text_from_prompt(prompt)

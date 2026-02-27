import io
import os
import requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from django.conf import settings
from django.core.files.storage import default_storage
from core.models.tarifario_hoteles import HotelTarifario, TarifaHabitacion
from core.models import Agencia
from decimal import Decimal
import vertexai
from vertexai.preview.vision_models import ImageGenerationModel
import base64

class MarketingService:
    @staticmethod
    def generate_instagram_story(hotel_id, agencia_id=None):
        """
        Generates a 1080x1920 JPG for Instagram Stories.
        """
        # 1. Fetch Data
        hotel = HotelTarifario.objects.get(pk=hotel_id)
        
        # Calculate "From" Price
        min_price = Decimal(0)
        currency = "USD"
        
        # Find lowest DBL rate
        tarifas = TarifaHabitacion.objects.filter(
            tipo_habitacion__hotel=hotel,
            tipo_tarifa='POR_PERSONA' # Assumed standard
        ).order_by('tarifa_dbl')
        
        if tarifas.exists():
            best_rate = tarifas.first()
            min_price = best_rate.tarifa_dbl
            currency = best_rate.moneda
        
        # Agency Branding
        agencia = None
        if agencia_id:
            agencia = Agencia.objects.filter(pk=agencia_id).first()
        
        if not agencia:
            agencia = Agencia.objects.filter(activa=True).first() # Fallback

        # 2. Canvas Setup (1080x1920)
        W, H = 1080, 1920
        canvas = Image.new('RGB', (W, H), (20, 20, 20))
        
        # 3. Load Main Image
        try:
            if hotel.imagen_principal:
                # Handle FileField (S3/Cloudinary or Local)
                try:
                     # Try opening directly if local
                    img_file = default_storage.open(hotel.imagen_principal.name)
                    bg_img = Image.open(img_file).convert('RGB')
                except:
                    # If url (Cloudinary), fetch it
                    url = hotel.imagen_principal.url
                    resp = requests.get(url, stream=True)
                    bg_img = Image.open(resp.raw).convert('RGB')
            else:
                 # Placeholder Gradient
                 bg_img = Image.new('RGB', (W, H), (50, 50, 100))
        except Exception as e:
            print(f"Error loading image: {e}")
            bg_img = Image.new('RGB', (W, H), (100, 50, 50))

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
        gradient = Image.new('L', (W, H), 0)
        draw_grad = ImageDraw.Draw(gradient)
        # Black gradient from 50% down
        for y in range(int(H * 0.4), H):
            alpha = int(255 * ((y - H * 0.4) / (H * 0.6)))
            draw_grad.line([(0, y), (W, y)], fill=alpha)
            
        overlay = Image.new('RGB', (W, H), (0, 0, 0))
        canvas.paste(overlay, (0, 0), mask=gradient)

        # 6. Typography
        draw = ImageDraw.Draw(canvas)
        
        # Fonts (Try to load system fonts or fallback)
        def load_font(size):
            try:
                # Windows standard path
                return ImageFont.truetype("arial.ttf", size)
            except:
                try:
                     # Linux standard path
                    return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", size)
                except:
                    return ImageFont.load_default()

        font_title = load_font(80)
        font_sub = load_font(40)
        font_price = load_font(70)
        
        # Helper Center Text
        def draw_text_center(y, text, font, color='white'):
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
        draw_text_center(H - margin_bottom, f"{hotel.destino.upper()}  |  {stars}", font_sub, color='#fbbf24')

        # Price Tag (Floating Top Right or Below name)
        if min_price > 0:
            price_text = f"Desde ${int(min_price)}"
            # Round pill background
            # bbox = draw.textbbox((0,0), price_text, font=font_price)
            # ... simple text for now
            draw_text_center(H - margin_bottom + 80, price_text, font_price, color='#4ade80')
            
        # Agency Branding (Top Center)
        if agencia and agencia.logo:
            try:
                if agencia.logo.name: # Local check
                    try:
                        f_logo = default_storage.open(agencia.logo.name)
                        logo_img = Image.open(f_logo).convert('RGBA')
                    except:
                        resp = requests.get(agencia.logo.url, stream=True)
                        logo_img = Image.open(resp.raw).convert('RGBA')
                        
                    # Resize logo (max width 400, max height 200)
                    logo_img.thumbnail((400, 200), Image.Resampling.LANCZOS)
                    lw, lh = logo_img.size
                    x_logo = int((W - lw) / 2)
                    y_logo = 150
                    canvas.paste(logo_img, (x_logo, y_logo), logo_img)
            except Exception as e:
                print(f"Logo error: {e}")
                draw_text_center(100, agencia.nombre, font_sub)
        else:
             if agencia:
                draw_text_center(100, agencia.nombre, font_sub)

        # 7. Output
        output = io.BytesIO()
        canvas.save(output, format='JPEG', quality=95)
        output.seek(0)
        return output

    @staticmethod
    def generate_social_caption(nombre_producto, destino, detalles, tono="AVENTURERO"):
        """
        Generates an Instagram/Facebook caption using Gemini AI.
        Agrega hashtags y emojis.
        """
        from core.services.gemini_client import generate_text_from_prompt
        
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
    def generate_email_newsletter(ofertas):
        """
        Generates an HTML Newsletter Summary for a list of deals.
        ofertas: List of dicts or objects with 'titulo', 'precio', 'destino'.
        """
        from core.services.gemini_client import generate_text_from_prompt
        
        lista_ofertas = ""
        for i, oferta in enumerate(ofertas, 1):
             # Manejo flexible de objetos o dicts
            titulo = oferta.get('titulo') if isinstance(oferta, dict) else getattr(oferta, 'titulo', 'Oferta')
            precio = oferta.get('precio') if isinstance(oferta, dict) else getattr(oferta, 'precio', 'Consultar')
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

    @staticmethod
    def generate_ai_promo_image(hotel_name, price, style="Luxurious", custom_text=None):
        """
        Generates a promotional image using Google Vertex AI (Imagen 3).
        Returns the base64 encoded image string.
        """
        try:
            # Configuración de Vertex AI
            project_id = settings.GCP_PROJECT_ID or 'travelhub-468322'
            location = settings.GCP_LOCATION or 'us-central1'
            
            # Inicializar Vertex AI
            vertexai.init(project=project_id, location=location)
            
            # Cargar Modelo (Intentar Imagen 3 luego Imagen 2)
            model_name = "image-3"
            try:
                model = ImageGenerationModel.from_pretrained(model_name)
            except Exception:
                # Fallback to Imagen 2
                print("Falling back to Imagen 2 (imagegeneration@006)")
                model_name = "imagegeneration@006"
                model = ImageGenerationModel.from_pretrained(model_name)
            
            # Construir Prompt
            prompt_text = custom_text or f"Special Offer: {hotel_name} starting at ${price}"
            base_prompt = f"""
            Create a high-quality, professional marketing poster for a hotel.
            Style: {style}.
            Subject: A stunning, photorealistic view of {hotel_name}, capturing a premium and inviting resort atmosphere.
            Text Requirement: The text "{prompt_text}" must be clearly visible, correctly spelled, and elegantly integrated into the composition (e.g., on a sign, overlay, or negative space).
            Format: Optimized for Instagram (Square 1:1 or Portrait).
            Lighting: Golden hour, warm and welcoming.
            """
            
            # Generar Imagen
            # Imagen 2 vs 3 parameters might differ slightly, but generate_images is consistent
            images = model.generate_images(
                prompt=base_prompt,
                number_of_images=1,
                language="en",
                aspect_ratio="1:1",
                safety_filter_level="block_some",
                person_generation="allow_adult"
            )
            
            if images:
                # Retornar Base64 para visualización directa
                img_bytes = images[0]._image_bytes
                b64_string = base64.b64encode(img_bytes).decode('utf-8')
                return {'image': b64_string, 'error': None}
            
            return {'image': None, 'error': 'No image generated by model'}
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"Error generating AI image: {e}")
            
            error_msg = str(e)
            if "403" in error_msg:
                error_msg = "Google Cloud Permission Denied (403). Check API Credentials."
            elif "429" in error_msg:
                error_msg = "Quota Exceeded. Try again later."
            elif "400" in error_msg:
                error_msg = "Bad Request. The prompt might be invalid."
                
            return {'image': None, 'error': error_msg}

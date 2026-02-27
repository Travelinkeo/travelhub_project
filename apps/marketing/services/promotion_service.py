import io
import os
import requests
import base64
from PIL import Image, ImageDraw, ImageFont
from django.conf import settings
from django.core.files.storage import default_storage
from decimal import Decimal
import vertexai
from vertexai.preview.vision_models import ImageGenerationModel
from core.models import HotelTarifario, TarifaHabitacion
from core.models import Agencia

class PromotionService:
    """
    Servicio para generar activos promocionales de alto impacto.
    Incluye integración con Vertex AI (Imagen 3) e historias de Instagram.
    """
    
    @staticmethod
    def generate_instagram_story(hotel_id, agencia_id=None):
        hotel = HotelTarifario.objects.get(pk=hotel_id)
        min_price = Decimal(0)
        
        tarifas = TarifaHabitacion.objects.filter(
            tipo_habitacion__hotel=hotel,
            tipo_tarifa='POR_PERSONA'
        ).order_by('tarifa_dbl')
        
        if tarifas.exists():
            min_price = tarifas.first().tarifa_dbl
        
        agencia = Agencia.objects.filter(pk=agencia_id).first() if agencia_id else Agencia.objects.filter(activa=True).first()

        W, H = 1080, 1920
        canvas = Image.new('RGB', (W, H), (20, 20, 20))
        
        try:
            if hotel.imagen_principal:
                img_file = default_storage.open(hotel.imagen_principal.name)
                bg_img = Image.open(img_file).convert('RGB')
            else:
                bg_img = Image.new('RGB', (W, H), (50, 50, 100))
        except Exception:
            bg_img = Image.new('RGB', (W, H), (100, 50, 50))

        # Aspect Fill
        bg_w, bg_h = bg_img.size
        ratio = max(W / bg_w, H / bg_h)
        new_size = (int(bg_w * ratio), int(bg_h * ratio))
        bg_img = bg_img.resize(new_size, Image.Resampling.LANCZOS)
        left = (new_size[0] - W) / 2
        top = (new_size[1] - H) / 2
        bg_img = bg_img.crop((left, top, left + W, top + H))
        canvas.paste(bg_img, (0, 0))
        
        # Gradient
        gradient = Image.new('L', (W, H), 0)
        draw_grad = ImageDraw.Draw(gradient)
        for y in range(int(H * 0.4), H):
            alpha = int(255 * ((y - H * 0.4) / (H * 0.6)))
            draw_grad.line([(0, y), (W, y)], fill=alpha)
        overlay = Image.new('RGB', (W, H), (0, 0, 0))
        canvas.paste(overlay, (0, 0), mask=gradient)

        draw = ImageDraw.Draw(canvas)
        try:
            font_title = ImageFont.truetype("arialbd.ttf", 80)
            font_sub = ImageFont.truetype("arial.ttf", 40)
            font_price = ImageFont.truetype("arialbd.ttf", 70)
        except:
            font_title = font_sub = font_price = ImageFont.load_default()

        def draw_text_center(y, text, font, color='white'):
            bbox = draw.textbbox((0, 0), text, font=font)
            text_w = bbox[2] - bbox[0]
            draw.text(((W - text_w) / 2, y), text, font=font, fill=color)

        draw_text_center(H - 400, hotel.nombre.upper(), font_title)
        draw_text_center(H - 300, f"{hotel.destino.upper()}  |  {'⭐' * hotel.categoria}", font_sub, color='#fbbf24')
        if min_price > 0:
            draw_text_center(H - 220, f"Desde ${int(min_price)}", font_price, color='#4ade80')

        output = io.BytesIO()
        canvas.save(output, format='JPEG', quality=95)
        output.seek(0)
        return output

    @staticmethod
    def generate_ai_promo_image(hotel_name, price, style="Luxurious", custom_text=None):
        try:
            vertexai.init(project=settings.GCP_PROJECT_ID, location=settings.GCP_LOCATION)
            model = ImageGenerationModel.from_pretrained("image-3")
            
            prompt_text = custom_text or f"Special Offer: {hotel_name} starting at ${price}"
            base_prompt = f"Create a high-quality, professional marketing poster for a hotel. Style: {style}. Subject: {hotel_name} resort. Text: {prompt_text}"
            
            images = model.generate_images(prompt=base_prompt, number_of_images=1, aspect_ratio="1:1")
            
            if images:
                img_bytes = images[0]._image_bytes
                return {'image': base64.b64encode(img_bytes).decode('utf-8'), 'error': None}
            return {'image': None, 'error': 'No image generated'}
        except Exception as e:
            return {'image': None, 'error': str(e)}

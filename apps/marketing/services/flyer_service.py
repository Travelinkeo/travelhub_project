import os
import requests
import random
from io import BytesIO
import logging
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from django.conf import settings

logger = logging.getLogger(__name__)

class FlyerService:
    """
    Servicio para generar imágenes promocionales (Flyers) para Telegram y Redes Sociales.
    Usa Pillow para composición de imágenes y Unsplash para fondos.
    """
    
    def __init__(self):
        self.width = 1080
        self.height = 1920 
        self.assets_dir = os.path.join(settings.BASE_DIR, 'static', 'images')
        self.output_dir = os.path.join(settings.MEDIA_ROOT, 'marketing')
        
        os.makedirs(self.output_dir, exist_ok=True)

    def _get_unsplash_image(self, query):
        access_key = os.environ.get('UNSPLASH_ACCESS_KEY')
        if not access_key:
            return None
            
        try:
            url = "https://api.unsplash.com/search/photos"
            params = {
                "query": f"{query} travel landscape",
                "orientation": "portrait",
                "per_page": 1,
                "client_id": access_key
            }
            
            response = requests.get(url, params=params, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data['results']:
                    image_url = data['results'][0]['urls']['regular']
                    img_response = requests.get(image_url, timeout=10)
                    if img_response.status_code == 200:
                        return BytesIO(img_response.content)
        except Exception as e:
            logger.error(f"Error Unsplash: {e}")
        return None

    def _get_random_background(self):
        bg_dir = os.path.join(self.assets_dir, 'backgrounds')
        if os.path.exists(bg_dir):
            files = [f for f in os.listdir(bg_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
            if files:
                return os.path.join(bg_dir, random.choice(files))
        return None

    def generate_flyer(self, destination: str = None, price: str = "$0", airline: str = None, hotel_id: int = None, agency_logo_path: str = None) -> BytesIO:
        try:
            hotel_data = None
            if hotel_id:
                from core.models.tarifario_hoteles import HotelTarifario
                hotel = HotelTarifario.objects.filter(pk=hotel_id).first()
                if hotel:
                    hotel_data = {
                        'nombre': hotel.nombre,
                        'destino': hotel.destino,
                        'categoria': hotel.categoria, # 1-5 stars
                    }
                    destination = hotel.destino
                    title_text = hotel.nombre
                else:
                    title_text = destination or "OFERTA"
            else:
                title_text = destination or "OFERTA"

            # Query Unsplash more intelligently
            if hotel_data:
                query = f"{hotel_data['nombre']} {hotel_data['destino']} hotel resort luxury"
            else:
                query = f"{destination} travel landscape"

            bg_stream = self._get_unsplash_image(query)
            img = None
            
            if bg_stream:
                img = Image.open(bg_stream).convert("RGBA")
            else:
                bg_path = self._get_random_background()
                if bg_path:
                    img = Image.open(bg_path).convert("RGBA")
            
            if img:
                # Resize and Crop to 1080x1920
                img_ratio = img.width / img.height
                target_ratio = self.width / self.height
                if img_ratio > target_ratio:
                    new_height = self.height
                    new_width = int(new_height * img_ratio)
                    img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                    left = (new_width - self.width) // 2
                    img = img.crop((left, 0, left + self.width, self.height))
                else:
                    new_width = self.width
                    new_height = int(new_width / img_ratio)
                    img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                    top = (new_height - self.height) // 2
                    img = img.crop((0, top, self.width, top + self.height))
            else:
                # Fallback Gradient
                img = Image.new('RGBA', (self.width, self.height), color='#0f172a')
                draw = ImageDraw.Draw(img)
                for i in range(self.height):
                    alpha = i / self.height
                    fill = (int(30*(1-alpha)), int(58*(1-alpha)), int(138*(1-alpha)))
                    draw.line([(0, i), (self.width, i)], fill=fill)

            # --- DESIGNER PRO ENHANCEMENTS ---
            
            # Card Setup (Centered)
            card_width = 900
            card_height = 800
            card_x = (self.width - card_width) // 2
            card_y = 500
            
            overlay = Image.new('RGBA', (self.width, self.height), (0, 0, 0, 0))
            draw_ov = ImageDraw.Draw(overlay)
            
            # Rounded Rectangle for Glass Card
            draw_ov.rounded_rectangle(
                [card_x, card_y, card_x + card_width, card_y + card_height],
                radius=60,
                fill=(255, 255, 255, 30), # Semi-transparent white
                outline=(255, 255, 255, 80),
                width=2
            )
            
            img = Image.alpha_composite(img, overlay)
            draw = ImageDraw.Draw(img)

            # Fonts setup
            try:
                # Try common system fonts or fallbacks
                f_bold = "arialbd.ttf"
                f_reg = "arial.ttf"
                font_title = ImageFont.truetype(f_bold, 100 if len(title_text) > 15 else 120)
                font_price = ImageFont.truetype(f_bold, 140)
                font_tag = ImageFont.truetype(f_bold, 40)
                font_stars = ImageFont.truetype(f_reg, 60)
            except IOError:
                font_title = font_price = font_tag = font_stars = ImageFont.load_default()

            # DRAW TEXT
            tag_text = "ESTADÍA DE ENSUEÑO" if hotel_id else "VIAJE DE ENSUEÑO"
            draw.text((self.width//2, card_y + 80), tag_text, font=font_tag, fill="#fbbf24", anchor="mm")
            
            # Title (Destination or Hotel Name)
            draw.text((self.width//2, card_y + 220), title_text.upper(), font=font_title, fill="white", anchor="mm")
            
            # Stars if Hotel
            if hotel_data and hotel_data.get('categoria'):
                stars = "★" * hotel_data['categoria']
                draw.text((self.width//2, card_y + 300), stars, font=font_stars, fill="#fbbf24", anchor="mm")

            # Divider
            lw = 200
            lx = (self.width - lw) // 2
            draw.line([lx, card_y+360, lx+lw, card_y+360], fill="white", width=4)

            # Price
            draw.text((self.width//2, card_y + 480), f"Desde {price}", font=font_price, fill="#10b981", anchor="mm")
            
            if hotel_data:
                location_text = f"UBICACIÓN: {hotel_data['destino'].upper()}"
                draw.text((self.width//2, card_y + 600), location_text, font=font_tag, fill="#cbd5e1", anchor="mm")
            elif airline:
                draw.text((self.width//2, card_y + 600), f"OPERADO POR: {airline.upper()}", font=font_tag, fill="#cbd5e1", anchor="mm")

            # CTA Button (Bottom)
            btn_w = 600
            btn_h = 120
            bx = (self.width - btn_w) // 2
            by = card_y + 680
            draw.rounded_rectangle([bx, by, bx+btn_w, by+btn_h], radius=30, fill="#6366f1")
            cta_text = "RESERVAR ESTADÍA" if hotel_id else "RESERVAR AHORA"
            draw.text((bx + btn_w//2, by + btn_h//2), cta_text, font=font_tag, fill="white", anchor="mm")

            # Final Signature
            draw.text((self.width//2, self.height - 150), "travelinkeo.com", font=font_tag, fill="white", anchor="mm")

            output = BytesIO()
            img = img.convert("RGB")
            img.save(output, format='JPEG', quality=95)
            output.seek(0)
            return output
        except Exception as e:
            logger.error(f"Error generando flyer: {e}")
            raise e

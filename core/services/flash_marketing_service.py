
import os
import requests
import random
from io import BytesIO
import logging
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from django.conf import settings

logger = logging.getLogger(__name__)

class FlashMarketingService:
    """
    Servicio para generar imágenes promocionales (Flyers) para Telegram.
    Usa Pillow para composición de imágenes.
    """
    
    def __init__(self):
        self.width = 1080
        self.height = 1920 # Formato Historia (9:16)
        self.assets_dir = os.path.join(settings.BASE_DIR, 'static', 'images')
        self.output_dir = os.path.join(settings.MEDIA_ROOT, 'marketing')
        
        # Asegurar directorio de salida
        os.makedirs(self.output_dir, exist_ok=True)

    def _get_unsplash_image(self, query):
        """Busca una imagen en Unsplash basada en el query"""
        access_key = os.environ.get('UNSPLASH_ACCESS_KEY')
        if not access_key:
            return None
            
        try:
            # Buscar foto vertical (portrait)
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
                    # Descargar imagen
                    img_response = requests.get(image_url, timeout=10)
                    if img_response.status_code == 200:
                        return BytesIO(img_response.content)
            
        except Exception as e:
            logger.error(f"Error Unsplash: {e}")
            
        return None

    def _get_random_background(self):
        """Busca una imagen de fondo en static/images/backgrounds o usa un color sólido"""
        bg_dir = os.path.join(self.assets_dir, 'backgrounds')
        if os.path.exists(bg_dir):
            files = [f for f in os.listdir(bg_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
            if files:
                return os.path.join(bg_dir, random.choice(files))
        
        # Fallback: Buscar en assets root
        files = [f for f in os.listdir(self.assets_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png')) and 'logo' not in f.lower()]
        if files:
             return os.path.join(self.assets_dir, random.choice(files))
             
        return None

    def _get_airline_logo_from_name(self, airline_name):
        """Busca el código IATA y descarga el logo de la aerolínea."""
        try:
            # 1. Cargar JSON de aerolíneas
            json_path = os.path.join(settings.BASE_DIR, 'core', 'data', 'airlines.json')
            import json
            if not os.path.exists(json_path):
                return None
                
            with open(json_path, 'r', encoding='utf-8') as f:
                airlines_data = json.load(f)
                
            # 2. Buscar código IATA (Fuzzy match simple)
            iata_code = None
            airline_name_lower = airline_name.lower().strip()
            
            for item in airlines_data:
                # Match exacto o 'contains'
                if airline_name_lower == item['name'].lower():
                    iata_code = item['code']
                    break
                elif airline_name_lower in item['name'].lower(): 
                   # Match parcial (ej: "Avianca" in "Avianca Aerovias...")
                   # Preferir match exacto, pero guardar este por si acaso
                   if not iata_code:
                       iata_code = item['code']
            
            if not iata_code:
                # Intento extra: Si el usuario puso el código IATA directamente (ej: "CM")
                if len(airline_name) == 2:
                     iata_code = airline_name.upper()

            if not iata_code:
                return None
                
            # 3. Descargar Logo de un CDN público (Kiwi/Aviasales)
            # URL format: https://pics.avs.io/200/200/{IATA}.png
            logo_url = f"https://pics.avs.io/200/200/{iata_code}.png"
            
            response = requests.get(logo_url, timeout=5)
            if response.status_code == 200:
                return Image.open(BytesIO(response.content)).convert("RGBA")
                
        except Exception as e:
            logger.error(f"Error fetching airline logo for {airline_name}: {e}")
            
        return None

    def generate_flyer(self, destination: str, price: str, airline: str = None, agency_logo_path: str = None) -> BytesIO:
        """
        Genera un flyer promocional.
        
        Args:
            destination (str): Destino (ej: "Madrid")
            price (str): Precio (ej: "$850")
            airline (str): Aerolínea (opcional)
            agency_logo_path (str): Ruta al logo de la agencia (opcional)
            
        Returns:
            BytesIO: El buffer de la imagen generada.
        """
        try:
            # 1. Crear Lienzo
            # Intentar Unsplash primero
            bg_stream = self._get_unsplash_image(destination)
            bg_path = None
            
            img = None
            
            if bg_stream:
                img = Image.open(bg_stream).convert("RGBA")
            else:
                bg_path = self._get_random_background()
                if bg_path:
                    img = Image.open(bg_path).convert("RGBA")
            
            if img:
                # Resize y Crop tipo 'Cover' al centro
                img_ratio = img.width / img.height
                target_ratio = self.width / self.height
                
                if img_ratio > target_ratio:
                    # Imagen más ancha, cortar lados
                    new_height = self.height
                    new_width = int(new_height * img_ratio)
                    img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                    left = (new_width - self.width) // 2
                    img = img.crop((left, 0, left + self.width, self.height))
                else:
                    # Imagen más alta, cortar arriba/abajo
                    new_width = self.width
                    new_height = int(new_width / img_ratio)
                    img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                    top = (new_height - self.height) // 2
                    img = img.crop((0, top, self.width, top + self.height))
            else:
                # Fondo gradiente por defecto (Azul TravelHub)
                img = Image.new('RGBA', (self.width, self.height), color='#0f172a')
                draw = ImageDraw.Draw(img)
                # Simular gradiente simple
                for i in range(self.height):
                    r = int(15 - (i/self.height)*10)
                    g = int(23 - (i/self.height)*10)
                    b = int(42 - (i/self.height)*10)
                    draw.line([(0, i), (self.width, i)], fill=(r, g, b))

            # 2. Overlay Oscuro (Para legibilidad)
            overlay = Image.new('RGBA', (self.width, self.height), (0, 0, 0, 100)) # 40% opacidad
            img = Image.alpha_composite(img, overlay)
            draw = ImageDraw.Draw(img)

            # 3. Cargar Fuentes
            try:
                # Intenta cargar Arial Bold para mayor impacto
                font_large = ImageFont.truetype("arialbd.ttf", 160)
                font_medium = ImageFont.truetype("arialbd.ttf", 80) # Precio en Negrita
                font_small = ImageFont.truetype("arial.ttf", 50)
                font_bold_small = ImageFont.truetype("arialbd.ttf", 50) 
            except IOError:
                try:
                    # Fallback a Arial normal si no hay Bold
                    font_large = ImageFont.truetype("arial.ttf", 160)
                    font_medium = ImageFont.truetype("arial.ttf", 80)
                    font_small = ImageFont.truetype("arial.ttf", 50)
                    font_bold_small = ImageFont.truetype("arial.ttf", 50)
                except IOError:
                    # Fallback total
                    font_large = ImageFont.load_default()
                    font_medium = ImageFont.load_default()
                    font_small = ImageFont.load_default()
                    font_bold_small = ImageFont.load_default()

            # 4. Dibujar Textos
            
            # Título: OFERTA FLASH (Arriba)
            draw.text((self.width//2, 200), "OFERTA FLASH", font=font_small, fill="#fca5a5", anchor="mm")
            
            # Destino (Centro) - En Negrita
            draw.text((self.width//2, 600), destination.upper(), font=font_large, fill="white", anchor="mm")
            
            # Precio (Debajo del destino, Grande) - En Negrita
            draw.text((self.width//2, 800), f"Desde {price}", font=font_medium, fill="#fbbf24", anchor="mm") # Ambar
            
            # Aerolinea (Opcional)
            if airline:
                # 1. Siempre Dibujar texto "Volando con X"
                draw.text((self.width//2, 920), f"Volando con {airline}", font=font_small, fill="#e2e8f0", anchor="mm")

                # 2. Intentar buscar Logo de Aerolinea
                airline_logo_img = self._get_airline_logo_from_name(airline)
                
                if airline_logo_img:
                    # Pegar logo de aerolínea (Más grande)
                    logo_w = 400 # Aumentado de 200 a 400
                    ratio = logo_w / airline_logo_img.width
                    logo_h = int(airline_logo_img.height * ratio)
                    airline_logo_img = airline_logo_img.resize((logo_w, logo_h), Image.Resampling.LANCZOS)
                    
                    logo_x = (self.width - logo_w) // 2
                    logo_y = 1000 # Debajo del texto (que está en 920)
                    
                    img.paste(airline_logo_img, (logo_x, logo_y), airline_logo_img)
            
            # 5. Agregar Logo Agencia (Firma Principal)
            # Prioridad: Logo Dark (Obsidian) > Logo Agencia > Logo Blanco Default
            logo_to_use = None
            
            if agency_logo_path and os.path.exists(agency_logo_path):
                logo_to_use = agency_logo_path
            else:
                default_logo = os.path.join(self.assets_dir, 'logo-blanco.png')
                if os.path.exists(default_logo):
                    logo_to_use = default_logo
                else:
                    alt_logo = os.path.join(self.assets_dir, 'Logo Blanco.png')
                    if os.path.exists(alt_logo):
                         logo_to_use = alt_logo

            if logo_to_use:
                try:
                    logo = Image.open(logo_to_use).convert("RGBA")
                    # Redimensionar logo a max 400px ancho (Firma más grande)
                    max_w = 400
                    max_h = 200
                    
                    # Calcular ratio para ajustar
                    w_ratio = max_w / logo.width
                    h_ratio = max_h / logo.height
                    scale = min(w_ratio, h_ratio)
                    
                    new_w = int(logo.width * scale)
                    new_h = int(logo.height * scale)
                    
                    logo = logo.resize((new_w, new_h), Image.Resampling.LANCZOS)
                    
                    # Pegar centrado al final (Firma)
                    logo_x = (self.width - new_w) // 2
                    logo_y = self.height - new_h - 150 # Margen inferior
                    
                    img.paste(logo, (logo_x, logo_y), logo)
                except Exception as e:
                    logger.error(f"Error cargando logo {logo_to_use}: {e}")

            # 6. Guardar en Memoria
            output = BytesIO()
            img = img.convert("RGB") # Convertir a RGB antes de guardar como JPG
            img.save(output, format='JPEG', quality=95)
            output.seek(0)
            
            return output

        except Exception as e:
            logger.error(f"Error generando flyer: {e}")
            raise e

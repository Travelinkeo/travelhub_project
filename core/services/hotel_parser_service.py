import os
import json
import logging
import fitz  # PyMuPDF
from PIL import Image
import io
import google.generativeai as genai
from django.conf import settings
from django.core.files.base import ContentFile
from django.db import transaction

# Modelos

    TarifarioProveedor,
    HotelTarifario,
    TipoHabitacion,
    TarifaHabitacion,
    Amenity,
    ImagenHotel
)

logger = logging.getLogger(__name__)

class HotelParserService:
    """
    Servicio 'Killer Feature' para ingerir Tarifarios de Hoteles (PDF) usando IA.
    Capacidades:
    1. Convierte PDF a Imágenes de Alta Resolución.
    2. Usa Gemini Vision para extraer:
       - Datos del Hotel (Nombre, Desc, Regimen, Categoria).
       - Tipos de Habitación y Capacidad.
       - Tablas de Tarifas (Fechas, Precios).
       - Amenities (Iconos).
    3. Detecta y recorta fotos del PDF para la galería.
    """

    def __init__(self, tarifario_id):
        self.tarifario = TarifarioProveedor.objects.get(pk=tarifario_id)
        self.api_key = getattr(settings, 'GEMINI_API_KEY', os.environ.get('GEMINI_API_KEY'))
        
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY no configurada.")
            
        genai.configure(api_key=self.api_key)
        # Usamos Flash para velocidad, o Pro para mejor razonamiento si es complejo
        # Actualizado a 2.0-flash según lista de modelos disponibles
        self.model = genai.GenerativeModel('gemini-2.0-flash') 

    def procesar_tarifario(self):
        """Punto de entrada principal"""
        pdf_path = self.tarifario.archivo_pdf.path
        logger.info(f"Iniciando procesamiento de tarifario: {pdf_path}")

        try:
            doc = fitz.open(pdf_path)
            
            # Iterar páginas (Por ahora limitamos para pruebas, luego todo)
            # Analizaremos cada página independiente, asumiendo que un hotel puede ocupar 1 o más páginas,
            # pero por simplificación inicial asumiremos 1 pagina = 1 hotel o parte de él.
            # Mejor estrategia: Enviar imagen y preguntar "¿Hay un hotel aquí? Extrae datos".
            
            for page_num in range(len(doc)):
                logger.info(f"Procesando página {page_num + 1}...")
                
                # 1. Renderizar Pagina a Imagen (300 DPI para mejor OCR)
                page = doc.load_page(page_num)
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2)) 
                img_data = pix.tobytes("png")
                pil_image = Image.open(io.BytesIO(img_data))
                
                # 2. Analizar con Gemini
                data = self._analizar_imagen_ia(pil_image)
                
                if data and data.get('es_pagina_hotel'):
                   self._guardar_datos_hotel(data, pil_image)

            doc.close()
            return True

        except Exception as e:
            logger.error(f"Error procesando tarifario: {e}")
            return False

    def _analizar_imagen_ia(self, image):
        prompt = """
        Eres un experto en turismo y extracción de datos. Analiza esta página de un tarifario hotelero digital y extrae la información estructurada.
        
        TAREA 1: DATOS DEL HOTEL
        Si ves un hotel nuevo en la página, extrae:
        - nombre (string)
        - destino (string, e.g., Morrocoy, Margarita)
        - descripcion_larga (string, el texto descriptivo comercial)
        - categoria (int 1-5, estima por estrellas o calidad visual)
        - regimen (string code: SO, SD, MP, PC, TI - Solo Alojamiento, Desayuno, Media Pension, Completa, Todo Incluido. Infiere del texto "Incluye desayunos", etc. Default SD)
        - amenidades (list of strings, e.g., "Wifi", "Piscina", "Estacionamiento", "Planta Electrica")
        - politicas (string, check-in, check-out, normas)
        - coordenadas_fotos (list of objects: {label: "Lobby/Habitacion/General", box_2d: [ymin, xmin, ymax, xmax]} Range 0-1000) -> IDENTIFICA LAS FOTOS CLAVE PARA RECORTARLAS.

        TAREA 2: HABITACIONES
        Lista las habitaciones:
        - nombre (string)
        - capacidad_adultos (int)
        - capacidad_ninos (int)
        - capacidad_total (int)

        TAREA 3: TARIFAS
        Extre la tabla de precios. Intenta normalizar fechas.
        - lista de objetos: {
            habitacion_nombre: "Matrimonial",
            fecha_inicio: "DD/MM/YYYY",
            fecha_fin: "DD/MM/YYYY",
            moneda: "USD" o "EUR",
            tarifa_dbl: float (precio por persona o por habitacion),
            tipo_tarifa: "POR_PERSONA" o "POR_HABITACION"
          }

        FORMATO JSON:
        {
            "es_pagina_hotel": true/false,
            "hotel": { ... },
            "habitaciones": [ ... ],
            "tarifas": [ ... ],
            "fotos": [ ... ]
        }
        """
        
        try:
            response = self.model.generate_content([prompt, image])
            text = response.text.strip()
            # Limpieza básica de Markdown
            if text.startswith('```json'):
                text = text[7:]
            if text.endswith('```'):
                text = text[:-3]
            return json.loads(text)
        except Exception as e:
            logger.error(f"Error IA: {e}")
            return None

    def _guardar_datos_hotel(self, data, source_image):
        hotel_data = data.get('hotel', {})
        if not hotel_data.get('nombre'): return

        print(f"DEBUG: Procesando {hotel_data['nombre']}...")
        try:
            with transaction.atomic():
                # 1. Crear/Actualizar Hotel
                # Buscamos por NOMBRE solamente para reusar el hotel existente
                # (Si existen homónimos en distintos destinos, la UI mostrará ambos, pero el slug único lo maneja el save)
                print("DEBUG: Buscando hotel existente...")
            
            defaults = {
                'tarifario': self.tarifario, # Actualizamos al tarifario más reciente
                'destino': hotel_data.get('destino') or 'Otro',
                'descripcion_larga': hotel_data.get('descripcion_larga') or '',
                'categoria': hotel_data.get('categoria') or 3,
                'politicas': hotel_data.get('politicas') or '',
                # Regimen default logic: get value, ensure string, slice 2. Fallback 'SD'
                'regimen_default': (hotel_data.get('regimen') or 'SD')[:2]
            }

            # Hardened logic: Avoid update_or_create to prevent MultipleObjectsReturned
            print(f"DEBUG: Ejecutando filter().first() para '{hotel_data['nombre']}'...")
            hotel = HotelTarifario.objects.filter(nombre=hotel_data['nombre']).first()
            if hotel:
                print(f"DEBUG: Hotel encontrado (ID: {hotel.id}). Actualizando...")
                # Update fields
                for key, value in defaults.items():
                    setattr(hotel, key, value)
                hotel.save()
                created = False
            else:
                print("DEBUG: Hotel no encontrado. Creando nuevo...")
                # Create new
                hotel = HotelTarifario.objects.create(nombre=hotel_data['nombre'], **defaults)
                created = True
            
            print(f"DEBUG: Hotel guardado (ID: {hotel.id}). Procesando amenidades...")
            # 2. Amenidades (Busca o crea)
            for amenidad_nombre in hotel_data.get('amenidades', []):
                amenity, _ = Amenity.objects.get_or_create(
                    nombre__iexact=amenidad_nombre,
                    defaults={'nombre': amenidad_nombre, 'icono_lucide': 'check'}
                )
                hotel.amenidades.add(amenity)
                
            # 3. Procesar Fotos (Recorte)
            fotos_coords = data.get('fotos', [])
            if fotos_coords:
                self._procesar_recortes(hotel, source_image, fotos_coords)

            # 4. Habitaciones y Tarifas
            # (Lógica simplificada para MVP: Crear habitaciones primero)
            mapa_habitaciones = {} # nombre -> objeto
            
            for hab_data in data.get('habitaciones', []):
                # Sanitize Integers (Avoid None/Null from JSON)
                cap_adultos = hab_data.get('capacidad_adultos')
                if cap_adultos is None: cap_adultos = 2
                
                cap_total = hab_data.get('capacidad_total')
                if cap_total is None: cap_total = 4
                
                hab, _ = TipoHabitacion.objects.get_or_create(
                    hotel=hotel,
                    nombre=hab_data['nombre'],
                    defaults={
                        'capacidad_adultos': int(cap_adultos),
                        'capacidad_ninos': int(hab_data.get('capacidad_ninos') or 0),
                        'capacidad_total': int(cap_total)
                    }
                )
                mapa_habitaciones[hab.nombre] = hab
            
            # 5. Tarifas (Asociar a habitaciones por coincidencia de nombre fuzzy o exacto)
            # ... Pendiente para V2 robusta, por ahora estructura básica ...

        except Exception as e:
            print(f"DEBUG: Error guardando hotel {hotel_data.get('nombre')}: {e}")
            logger.error(f"Error guardando hotel: {e}")
            # Re-raise to ensure transaction rollback if needed, or just log
            raise e
    def _procesar_recortes(self, hotel, source_image, fotos_coords):
        """
        Recorta sub-imágenes basadas en coordenadas del array `fotos_coords`
        y las guarda como ImagenHotel.
        """
        from django.core.files.base import ContentFile
        import io

        width, height = source_image.size

        for i, foto_data in enumerate(fotos_coords):
            try:
                # Coordenadas vienen en rango 0-1000 (standard de Gemini detection)
                # Formato esperado: { "label": "Lobby", "box_2d": [ymin, xmin, ymax, xmax] }
                box = foto_data.get('box_2d')
                if not box or len(box) != 4: continue
                
                ymin, xmin, ymax, xmax = box
                
                # Convertir a pixeles absolutos
                left = (xmin / 1000) * width
                top = (ymin / 1000) * height
                right = (xmax / 1000) * width
                bottom = (ymax / 1000) * height
                
                # Margen opcional
                
                # Crop
                crop_img = source_image.crop((left, top, right, bottom))
                
                # Guardar en memoria
                img_io = io.BytesIO()
                crop_img.save(img_io, format='JPEG', quality=85)
                
                # Guardar Modelo
                tipo_map = {
                    'Habitacion': 'HABITACION', 
                    'Comida': 'COMIDA', 
                    'Playa': 'PLAYA', 
                    'Piscina': 'PLAYA',
                    'General': 'GENERAL'
                }
                tipo_detectado = tipo_map.get(foto_data.get('label', 'General'), 'GENERAL')
                
                img_instance = ImagenHotel(
                    hotel=hotel,
                    titulo=f"Foto {i+1} - {foto_data.get('label', '')}",
                    tipo=tipo_detectado,
                    es_portada=(i==0 and not hotel.imagen_principal) # Usar la primera como portada si no hay
                )
                
                file_name = f"{hotel.slug}_foto_{i}.jpg"
                img_instance.imagen.save(file_name, ContentFile(img_io.getvalue()), save=True)
                
                # Si es portada, asignar también al hotel
                if img_instance.es_portada:
                    hotel.imagen_principal = img_instance.imagen
                    hotel.save()
                    
            except Exception as e:
                logger.error(f"Error recortando foto {i}: {e}")

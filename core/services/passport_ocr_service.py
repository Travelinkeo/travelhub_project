import os
import json
import logging
from django.conf import settings
from google import genai
from google.genai import types
from PIL import Image

logger = logging.getLogger(__name__)

class PassportOCRService:
    """
    Servicio para extracción de datos de pasaportes utilizando Google Gemini Vision.
    MIGRADO a SDK google-genai (v1.x).
    """
    MODEL_NAME = "gemini-2.0-flash"  # gemini-2.5-flash cuando esté GA

    def __init__(self):
        self.api_key = getattr(settings, 'GEMINI_API_KEY', None) or os.environ.get('GEMINI_API_KEY')
        if self.api_key:
            self.client = genai.Client(api_key=self.api_key)
        else:
            logger.warning("GEMINI_API_KEY no configurada. El servicio OCR no funcionará.")
            self.client = None

    def process_passport_image(self, image_file):
        """
        Procesa una imagen de pasaporte (ruta o objeto archivo) y extrae datos JSON.
        """
        if not self.client:
            return {
                'success': False,
                'error': 'API Key de Gemini no configurada.',
                'data': {}
            }

        try:
            # Cargar imagen (Soporta path o file-like object)
            img = Image.open(image_file)
            img_bytes = img.tobytes()
            # Convertir imagen PIL a bytes png para enviar inline
            from io import BytesIO
            buf = BytesIO()
            img.save(buf, format="PNG")
            img_bytes = buf.getvalue()

            prompt = """
            Act as an expert OCR system for Travel Documents.
            Analyze this passport image and extract the following information in strict JSON format.
            If a field is not visible or unclear, use null.
            
            Required fields:
            - numero_pasaporte (string)
            - apellidos (string)
            - nombres (string)
            - nacionalidad (ISO 3 country code, e.g., VEN, USA, ESP)
            - fecha_nacimiento (YYYY-MM-DD)
            - fecha_vencimiento (YYYY-MM-DD)
            - sexo (M or F)
            - pais_emision (ISO 3 country code)
            - face_coordinates (array of 4 integers: [ymin, xmin, ymax, xmax] relative to 1000x1000 scale. e.g. [200, 100, 500, 400])

            Output only the valid JSON.
            """

            response = self.client.models.generate_content(
                model=self.MODEL_NAME,
                contents=[
                    types.Part.from_bytes(data=img_bytes, mime_type="image/png"),
                    prompt
                ]
            )

            # Limpiar respuesta (quitar backticks de markdown si existen)
            text_response = response.text.strip()
            if text_response.startswith('```json'):
                text_response = text_response[7:]
            if text_response.endswith('```'):
                text_response = text_response[:-3]
            
            data = json.loads(text_response)
            
            # Procesar Recorte de Cara
            face_coords = data.get('face_coordinates')
            if face_coords and len(face_coords) == 4:
                try:
                    import base64
                    from io import BytesIO
                    
                    ymin, xmin, ymax, xmax = face_coords
                    width, height = img.size
                    
                    # Convertir coordenadas relativas (1000x1000) a absolutas
                    left = (xmin / 1000) * width
                    top = (ymin / 1000) * height
                    right = (xmax / 1000) * width
                    bottom = (ymax / 1000) * height
                    
                    # Margen de seguridad (10%)
                    margin_w = (right - left) * 0.1
                    margin_h = (bottom - top) * 0.1
                    
                    crop_box = (
                        max(0, left - margin_w),
                        max(0, top - margin_h),
                        min(width, right + margin_w),
                        min(height, bottom + margin_h)
                    )
                    
                    face_img = img.crop(crop_box)
                    
                    # Convertir a Base64
                    buffered = BytesIO()
                    face_img.save(buffered, format="JPEG")
                    img_str = base64.b64encode(buffered.getvalue()).decode()
                    data['face_image_base64'] = f"data:image/jpeg;base64,{img_str}"
                    
                except Exception as e:
                    logger.warning(f"Error recortando cara: {e}")
                    data['face_image_base64'] = None

            # Validación básica
            if not data.get('numero_pasaporte'):
                return {'success': False, 'error': 'No se pudo detectar el número de pasaporte', 'data': data}

            # Enriquecer con IDs de base de datos para Países
            try:
                from core.models_catalogos import Pais
                
                # Resolver Nacionalidad
                nac_iso = data.get('nacionalidad')
                if nac_iso and len(nac_iso) == 3:
                    pais_nac = Pais.objects.filter(codigo_iso_3=nac_iso).first()
                    if pais_nac:
                        data['nacionalidad'] = pais_nac.pk
                        
                # Resolver País Emisión
                pais_emision_iso = data.get('pais_emision')
                if pais_emision_iso and len(pais_emision_iso) == 3:
                    pais_em = Pais.objects.filter(codigo_iso_3=pais_emision_iso).first()
                    if pais_em:
                        data['pais_emision'] = pais_em.pk
                        
            except Exception as db_err:
                logger.warning(f"No se pudieron resolver los IDs de paises: {db_err}")

            return {
                'success': True,
                'data': data,
                'confidence': 'HIGH' # Gemini suele ser muy preciso
            }

        except Exception as e:
            logger.error(f"Error procesando pasaporte con Gemini: {e}")
            return {
                'success': False,
                'error': f"Error de procesamiento: {str(e)}",
                'data': {}
            }

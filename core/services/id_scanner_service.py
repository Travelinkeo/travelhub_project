import logging
import io
from PIL import Image
from django.core.files.base import ContentFile
from core.services.ai_engine import ai_engine
from core.models.ai_schemas import CedulaOCRSchema

logger = logging.getLogger(__name__)

class IDScannerService:
    """
    Servicio especializado en el escaneo de documentos de identidad,
    extracción de datos demográficos y recorte de rostros (Computer Vision).
    """

    @staticmethod
    def procesar_cedula(image_file, agencia=None):
        try:
            print("[SISTEMA] Procesando imagen...")
            image_data = image_file.read()
            image_file.seek(0)
            
            content_list = [{"mime_type": "image/jpeg", "data": image_data}]
            
            system_prompt = (
                "Eres un sistema experto en OCR de documentos venezolanos. "
                "Analiza esta imagen de una Cédula de Identidad de la República Bolivariana de Venezuela.\n\n"
                "INSTRUCCIONES PRECISAS:\n"
                "1. APELLIDOS: Busca el campo 'APELLIDOS' o 'APELLIDO'. Extrae SOLO los apellidos en MAYÚSCULAS.\n"
                "2. NOMBRES: Busca el campo 'NOMBRES' o 'NOMBRE'. Extrae SOLO los nombres en MAYÚSCULAS.\n"
                "3. CÉDULA: El número de cédula está precedido por 'V-' o 'E-'. Extrae SOLO los dígitos numéricos (Ej: si es V-12345678, devuelve 12345678).\n"
                "4. FECHA DE NACIMIENTO: Busca 'FECHA DE NACIMIENTO' o 'NAC:'. Convierte al formato YYYY-MM-DD.\n"
                "5. PORTRAIT_BBOX: Detecta la foto/rostro del titular. Devuelve coordenadas [ymin, xmin, ymax, xmax] en escala 0-1000. La foto suele estar a la izquierda del documento.\n\n"
                "REGLAS CRÍTICAS:\n"
                "- Si un campo es ilegible o no existe, devuelve null (NO inventes datos).\n"
                "- NUNCA uses textos como 'SIN NOMBRE', 'N/A', o 'DESCONOCIDO'.\n"
                "- Los nombres y apellidos deben estar en MAYÚSCULAS sin acentos.\n"
                "- El portrait_bbox debe encuadrar SOLO el rostro humano, no todo el documento."
            )
            
            resultado_raw = ai_engine.call_gemini(
                prompt="Analiza la cédula venezolana y extrae: apellidos, nombres, número de cédula (solo dígitos), fecha de nacimiento en YYYY-MM-DD, y las coordenadas del rostro (portrait_bbox).",
                content_list=content_list,
                response_schema=CedulaOCRSchema,
                system_instruction=system_prompt
            )
            
            # === NORMALIZACIÓN DE CLAVES ===
            # Gemini devuelve claves en MAYÚSCULAS. Las mapeamos a snake_case.
            if isinstance(resultado_raw, dict):
                KEY_MAP = {
                    'apellidos': 'apellidos', 'APELLIDOS': 'apellidos',
                    'nombres': 'nombres', 'NOMBRES': 'nombres',
                    'cedula': 'cedula', 'CEDULA': 'cedula', 'CÉDULA': 'cedula',
                    'fecha_nacimiento': 'fecha_nacimiento',
                    'FECHA DE NACIMIENTO': 'fecha_nacimiento',
                    'FECHA_NACIMIENTO': 'fecha_nacimiento',
                    'portrait_bbox': 'portrait_bbox', 'PORTRAIT_BBOX': 'portrait_bbox',
                }
                resultado_raw = {
                    KEY_MAP.get(k, k.lower().replace(' ', '_')): v
                    for k, v in resultado_raw.items()
                }

            # Si Gemini devuelve una lista, tomamos el primer elemento
            resultado = resultado_raw[0] if isinstance(resultado_raw, list) else resultado_raw

            import re
            cedula_raw = str(resultado.get('cedula', '0'))
            cedula_limpia = re.sub(r'[^0-9]', '', cedula_raw) or "foto"
            
            recorte_final = None
            bbox = resultado.get('portrait_bbox', [0, 0, 0, 0])
            
            if any(coord > 0 for coord in bbox):
                try:
                    img = Image.open(image_file)
                    w, h = img.size
                    ymin, xmin, ymax, xmax = bbox
                    face_crop = img.crop((xmin*w/1000, ymin*h/1000, xmax*w/1000, ymax*h/1000))
                    buffer = io.BytesIO()
                    face_crop.save(buffer, format="JPEG")
                    recorte_final = ContentFile(buffer.getvalue(), name=f"face_{cedula_limpia}.jpg")
                except Exception as e:
                    logger.error(f"Error recorte: {e}")

            resultado['foto_recortada'] = recorte_final
            return resultado
        except Exception as e:
            logger.error(f"Error crítico: {e}")
            return {"error": str(e)}

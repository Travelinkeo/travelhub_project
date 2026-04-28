import logging
import base64
import os
from io import BytesIO
from typing import Dict, Any, Optional
from django.conf import settings
from django.db import models
from PIL import Image

from ..services.ai_engine import ai_engine
from ..models.ai_schemas import PasaporteOCRSchema
from ..prompts import PASSPORT_OCR_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

class OCRService:
    """
    SERVICIO DE VISIÓN ARTIFICIAL (IA MULTIMODAL):
    Especializado en el reconocimiento y extracción de datos de documentos de identidad.
    Utiliza el motor de Gemini Vision con esquemas estructurados de Pydantic.
    """

    def procesar_pasaporte(self, file_content: bytes, mime_type: str = "image/jpeg") -> Dict[str, Any]:
        """
        Extrae datos biométricos de una imagen de pasaporte usando Gemini Vision.
        
        Args:
            file_content: El contenido binario de la imagen.
            mime_type: El tipo MIME (image/png, image/jpeg, etc.)
            
        Returns:
            Dict estructurado según PasaporteOCRSchema o error.
        """
        logger.info(f"📸 Iniciando OCR de Pasaporte con IA Multimodal (Mime: {mime_type})")
        
        try:
            # 1. Preparar el contenido para Gemini (Formato Dict esperado por call_gemini)
            img_data = {
                "mime_type": mime_type,
                "data": base64.b64encode(file_content).decode("utf-8")
            }
            
            # 2. Llamada estructurada a través de AIEngine
            # Usamos el modelo Vision que definimos en ai_engine.VISION_MODEL
            resultado = ai_engine.call_gemini(
                prompt="Analiza este documento de identidad y extrae los datos del pasajero de forma estructurada.",
                content_list=[img_data],
                response_schema=PasaporteOCRSchema,
                system_instruction=PASSPORT_OCR_SYSTEM_PROMPT
            )
            
            # 3. Post-procesamiento: Resolución de Catálogos (Países)
            # El formulario espera PKs de Pais, no strings
            try:
                from core.models_catalogos import Pais
                # Resolver Nacionalidad
                nac_iso = resultado.get('nacionalidad')
                if nac_iso:
                    pais_nac = Pais.objects.filter(
                        models.Q(codigo_iso_3=nac_iso.upper()) | 
                        models.Q(nombre__icontains=nac_iso)
                    ).first()
                    if pais_nac:
                        resultado['nacionalidad_id'] = pais_nac.pk
                        
                # Resolver País Emisión
                pais_em_iso = resultado.get('pais_emision')
                if pais_em_iso:
                    pais_em = Pais.objects.filter(
                        models.Q(codigo_iso_3=pais_em_iso.upper()) | 
                        models.Q(nombre__icontains=pais_em_iso)
                    ).first()
                    if pais_em:
                        resultado['pais_emision_id'] = pais_em.pk
            except Exception as db_err:
                logger.warning(f"⚠️ Error al resolver IDs de países en OCR: {db_err}")

            logger.info(f"✅ OCR Completado con éxito para: {resultado.get('nombres')} {resultado.get('apellidos')}")
            resultado["success"] = True
            return resultado

        except Exception as e:
            logger.exception(f"❌ Fallo crítico en el servicio de OCR: {e}")
            return {"error": str(e), "success": False}

    def comprimir_imagen(self, image_bytes: bytes, max_size_kb: int = 500) -> bytes:
        """
        Comprime imágenes pesadas antes de enviarlas a la API para ahorrar 
        ancho de banda y mejorar el tiempo de respuesta.
        """
        try:
            img = Image.open(BytesIO(image_bytes))
            # Convertir a RGB si es necesario (ej: PNG con transparencia)
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            out_buffer = BytesIO()
            quality = 85
            img.save(out_buffer, format='JPEG', quality=quality, optimize=True)
            
            # Si sigue siendo muy grande, bajamos la calidad agresivamente hasta 50
            while out_buffer.tell() > max_size_kb * 1024 and quality > 50:
                out_buffer = BytesIO()
                quality -= 10
                img.save(out_buffer, format='JPEG', quality=quality, optimize=True)
            
            return out_buffer.getvalue()
        except Exception as e:
            logger.warning(f"No se pudo comprimir la imagen, enviando original: {e}")
            return image_bytes

# Instancia singleton para facilitar su uso en tareas de Celery
ocr_service = OCRService()

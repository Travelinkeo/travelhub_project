# Archivo: core/views/boleto_views.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from django.core.files.base import ContentFile
import os
import logging

# Importar el servicio de parseo y los modelos de Django
from ..services.ticket_parser_service import orquestar_parseo_de_boleto, generar_pdf_en_memoria
from ..models.boletos import BoletoImportado # CORREGIDO: Import desde el submódulo correcto

from django.conf import settings

logger = logging.getLogger(__name__)

class BoletoUploadAPIView(APIView):
    """
    Endpoint para subir un archivo de boleto (PDF/TXT), parsearlo
    de forma inteligente (IA con fallback a Regex) y guardar los
    resultados en la base de datos.
    """
    parser_classes = (MultiPartParser, FormParser)
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        logger.info("-> BoletoUploadAPIView.post() ha sido alcanzado.")
        
        archivo_subido = request.FILES.get('boleto_file')
        if not archivo_subido:
            logger.warning("Intento de subida sin archivo.")
            return Response(
                {"error": "No se proporcionó ningún archivo en el campo 'boleto_file'."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 1. Orquestar el parseo del boleto usando el servicio
        datos_parseados, mensaje = orquestar_parseo_de_boleto(archivo_subido)
        
        if not datos_parseados:
            logger.error(f"Fallo en el parseo del archivo '{archivo_subido.name}': {mensaje}")
            return Response(
                {"error": mensaje},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 2. Guardar el boleto original y los datos parseados en el modelo
        try:
            boleto_importado = BoletoImportado.objects.create(
                archivo_boleto=archivo_subido, # CORREGIDO: Nombre del campo
                datos_parseados=datos_parseados,
                # subido_por=request.user # ELIMINADO: El modelo no tiene este campo
            )
            
        except Exception as e:
            logger.exception(f"Error al guardar el boleto '{archivo_subido.name}' en la base de datos.")
            return Response(
                {"error": f"Error al guardar en la base de datos: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            
        # 3. (Opcional) Generar el PDF final y guardarlo en el modelo
        try:
            from django.core.files.storage import default_storage
            
            logger.info(f"Iniciando generación de PDF para boleto {boleto_importado.id_boleto_importado}")
            logger.info(f"Storage backend: {default_storage.__class__.__name__}")
            logger.info(f"USE_CLOUDINARY: {getattr(settings, 'USE_CLOUDINARY', False)}")
            
            plantilla_path = os.path.join(settings.BASE_DIR, 'core', 'templates', 'core', 'ticket_template_sabre.html')
            pdf_bytes = generar_pdf_en_memoria(datos_parseados, plantilla_path)
            
            if pdf_bytes:
                logger.info(f"PDF generado, tamaño: {len(pdf_bytes)} bytes")
                numero_boleto = datos_parseados.get("reserva", {}).get("numero_boleto", "SIN_BOLETO")
                nombre_archivo_generado = f"Boleto_{numero_boleto}_{boleto_importado.id_boleto_importado}.pdf"
                logger.info(f"Nombre de archivo: {nombre_archivo_generado}")
                
                # CORREGIDO: Nombre del campo 'archivo_pdf_generado'
                boleto_importado.archivo_pdf_generado.save(nombre_archivo_generado, ContentFile(pdf_bytes), save=True)
                
                # Verificar que se guardó
                if boleto_importado.archivo_pdf_generado:
                    url = boleto_importado.archivo_pdf_generado.url
                    logger.info(f"✅ PDF guardado exitosamente")
                    logger.info(f"   Ruta: {boleto_importado.archivo_pdf_generado.name}")
                    logger.info(f"   URL: {url}")
                    logger.info(f"   Storage: {boleto_importado.archivo_pdf_generado.storage.__class__.__name__}")
                else:
                    logger.warning("⚠️ archivo_pdf_generado está vacío después de guardar")
        except Exception as e:
            logger.warning(f"❌ No se pudo generar el PDF para el boleto {boleto_importado.id_boleto_importado}, pero el parseo fue exitoso. Error: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())


        logger.info(f"-> Boleto {boleto_importado.id_boleto_importado} procesado y guardado exitosamente.")

        # 4. Devolver una respuesta exitosa con los datos extraídos
        return Response(
            {
                "mensaje": "Boleto procesado y guardado con éxito.",
                "id_boleto_importado": boleto_importado.id_boleto_importado,
                "datos_extraidos": datos_parseados
            },
            status=status.HTTP_201_CREATED
        )

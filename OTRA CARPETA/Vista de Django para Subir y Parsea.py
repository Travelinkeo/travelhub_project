from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from django.core.files.base import ContentFile
import os
import logging

# Importar el servicio de parseo y los modelos de Django
# Asegúrate de que la ruta de importación sea correcta según tu estructura.
# Por ejemplo: from ..services.ticket_parser_service import ...
from ..services.ticket_parser_service import orquestar_parseo_de_boleto, generar_pdf_en_memoria
from ..models import BoletoImportado, VentaParseMetadata

# Importar settings para construir rutas de forma segura
from django.conf import settings

# Configurar un logger para esta vista
logger = logging.getLogger(__name__)

class BoletoUploadAPIView(APIView):
    """
    Endpoint para subir un archivo de boleto (PDF/TXT), parsearlo
    de forma inteligente (IA con fallback a Regex) y guardar los
    resultados en la base de datos.
    """
    parser_classes = (MultiPartParser, FormParser)
    permission_classes = [IsAuthenticated] # Proteger el endpoint para usuarios logueados

    def post(self, request, *args, **kwargs):
        logger.info("-> Endpoint BoletoUploadAPIView alcanzado.")
        
        archivo_subido = request.FILES.get('boleto_file')
        if not archivo_subido:
            logger.warning("Intento de subida sin el archivo 'boleto_file'.")
            return Response(
                {"error": "No se proporcionó ningún archivo en el campo 'boleto_file'."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 1. Orquestar el parseo del boleto usando el servicio centralizado
        datos_parseados, mensaje = orquestar_parseo_de_boleto(archivo_subido)
        
        if not datos_parseados:
            logger.error(f"Fallo en el parseo del archivo '{archivo_subido.name}': {mensaje}")
            return Response(
                {"error": mensaje, "detalle": "No se pudo extraer información del boleto."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 2. Guardar el boleto original y los datos parseados en el modelo
        try:
            boleto_importado = BoletoImportado.objects.create(
                archivo_original=archivo_subido,
                datos_parseados=datos_parseados, # Guardar el JSON completo
                subido_por=request.user 
            )
            
            # (Opcional pero recomendado) Poblar el modelo VentaParseMetadata
            reserva_info = datos_parseados.get('reserva', {})
            VentaParseMetadata.objects.create(
                boleto=boleto_importado,
                pnr=reserva_info.get('codigo_reservacion'),
                numero_boleto=reserva_info.get('numero_boleto'),
                fecha_emision=reserva_info.get('fecha_emision_iso'),
            )

        except Exception as e:
            logger.exception(f"Error al guardar el boleto '{archivo_subido.name}' en la base de datos.")
            return Response(
                {"error": "Ocurrió un error interno al guardar la información.", "detalle": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            
        # 3. (Opcional) Generar y guardar el PDF estandarizado
        try:
            plantilla_path = os.path.join(settings.BASE_DIR, 'core', 'templates', 'core', 'ticket_template_sabre.html')
            pdf_bytes = generar_pdf_en_memoria(datos_parseados, plantilla_path)
            
            if pdf_bytes:
                numero_boleto = reserva_info.get("numero_boleto", "SIN_BOLETO")
                nombre_archivo_generado = f"BoletoEstandar_{numero_boleto}_{boleto_importado.id}.pdf"
                
                # Guardar el archivo en un campo FileField (asumiendo que exista en el modelo)
                if hasattr(boleto_importado, 'archivo_generado'):
                    boleto_importado.archivo_generado.save(nombre_archivo_generado, ContentFile(pdf_bytes), save=True)
        except Exception as e:
            logger.warning(f"No se pudo generar el PDF estandarizado para el boleto {boleto_importado.id}. Error: {str(e)}")


        logger.info(f"-> Boleto {boleto_importado.id} procesado y guardado exitosamente.")

        # 4. Devolver una respuesta exitosa con los datos extraídos
        return Response(
            {
                "mensaje": "Boleto procesado y guardado con éxito.",
                "id_boleto_importado": boleto_importado.id,
                "datos_extraidos": datos_parseados
            },
            status=status.HTTP_201_CREATED
        )


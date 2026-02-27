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
from ..services.venta_automation import VentaAutomationService # AUTOMATION NIVEL 4
from apps.finance.services.invoice_service import InvoiceService
from apps.bookings.models import BoletoImportado, Venta
from apps.crm.models import Cliente

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
        # AHORA retorna una LISTA de dicts (Multi-Pax support)
        datos_parseados_list, mensaje = orquestar_parseo_de_boleto(archivo_subido)
        
        if not datos_parseados_list:
            logger.error(f"Fallo en el parseo del archivo '{archivo_subido.name}': {mensaje}")
            return Response(
                {"error": mensaje},
                status=status.HTTP_400_BAD_REQUEST
            )

        # BACKWARD COMPATIBILITY: Si retorna dict único (por error o legacy), lo envolvemos
        if isinstance(datos_parseados_list, dict):
            datos_parseados_list = [datos_parseados_list]

        logger.info(f"📋 Procesando {len(datos_parseados_list)} boletos extraídos del archivo.")
        
        boletos_creados_ids = []
        resultados_json = []

        # 2. Iterar sobre cada ticket extraído
        for idx, datos_parseados in enumerate(datos_parseados_list):
            try:
                # IMPORTANTE: Resetear el puntero del archivo al inicio para cada guardado?
                # Django ImageField/FileField maneja esto, pero para seguridad:
                if idx > 0: archivo_subido.seek(0) 
                
                # Crear copia del archivo para cada registro (opcional, o referenciar el mismo)
                # Django al guardar duplica el archivo físico si no se maneja con cuidado.
                # Para MVP: Dejar que Django maneje el archivo.
                
                boleto_importado = BoletoImportado.objects.create(
                    archivo_boleto=archivo_subido, 
                    datos_parseados=datos_parseados,
                )
                
                # Asignar agencia
                agencia_usuario = None
                if hasattr(request.user, 'agencias'):
                    usuario_agencia = request.user.agencias.filter(activo=True).first()
                    if usuario_agencia:
                        agencia_usuario = usuario_agencia.agencia
                        boleto_importado.agencia = agencia_usuario
                        boleto_importado.save()

                # --- AUTOMATION START (NIVEL 4) ---
                try:
                    proveedor_id = request.data.get('proveedor_id')
                    if proveedor_id in ['undefined', 'null', '']:
                        proveedor_id = None
                    
                    if agencia_usuario:
                        logger.info(f"Iniciando automatización de venta para boleto {boleto_importado.id_boleto_importado} (Pax: {idx+1})")
                        venta_creada = VentaAutomationService.crear_venta_desde_parser(
                            datos_parseados, 
                            agencia=agencia_usuario, 
                            usuario=request.user,
                            proveedor_id=proveedor_id
                        )
                        boleto_importado.venta_asociada = venta_creada
                        boleto_importado.save()
                        logger.info(f"✅ Venta {venta_creada.id_venta} creada automáticamente")
                except Exception as e_auto:
                    logger.error(f"⚠️ Error en automatización de venta: {e_auto}")
                # --- AUTOMATION END ---
                
                # 3. Generar PDF
                try:
                    # Usamos la nueva lógica centralizada en ticket_parser_service para PDF
                    service._generar_pdf_boleto(boleto_importado, datos_parseados)
                    logger.info(f"✅ PDF procesado para boleto {boleto_importado.id_boleto_importado}")
                except Exception as e_pdf:
                    logger.warning(f"❌ Error generando PDF para boleto {boleto_importado.id_boleto_importado}: {e_pdf}")

                logger.info(f"-> Boleto {boleto_importado.id_boleto_importado} procesado exitosamente.")
                
                boletos_creados_ids.append(boleto_importado.id_boleto_importado)
                resultados_json.append(datos_parseados)

            except Exception as e_loop:
                logger.error(f"❌ Error procesando ticket index {idx}: {e_loop}")
                continue

        if not boletos_creados_ids:
             return Response(
                {"error": "No se pudieron crear boletos (Error interno en loop)."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # 4. Devolver una respuesta exitosa
        # Nota: El frontend puede esperar un objeto singular si antes lo hacía.
        # Si devolvemos 'datos_extraidos' como lista, el frontend debe estar preparado?
        # Asumimos que el frontend muestra el último o maneja la lista.
        # Para compatibilidad, devolvemos el PRIMERO en 'datos_extraidos' y añadimos 'todos'
        
        return Response(
            {
                "mensaje": f"Se han procesado {len(boletos_creados_ids)} boletos con éxito.",
                "id_boleto_importado": boletos_creados_ids[0], # ID del primero para compatibilidad
                "datos_extraidos": resultados_json[0], # Datos del primero para compatibilidad
                "boletos_creados": boletos_creados_ids, # Lista completa de IDs
                "todos_datos_extraidos": resultados_json # Lista completa de datos
            },
            status=status.HTTP_201_CREATED
        )

class BoletoRetryParseAPIView(APIView):
    """
    Fuerza el re-parseo de un boleto importado existente.
    Útil si el primer intento falló o si se ha mejorado el motor de parseo.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            from ..services.ticket_parser_service import TicketParserService
            service = TicketParserService()
            
            # El servicio se encarga de re-extraer texto, re-parsear,
            # actualizar campos y re-generar PDF.
            resultado = service.procesar_boleto(pk)
            
            if resultado:
                return Response({
                    "mensaje": "Boleto re-procesado con éxito.",
                    "id_boleto_importado": pk,
                    "resultado": str(resultado) # Puede ser la Venta o el dict de Review Required
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    "error": "El re-procesamiento falló. Revise el log de parseo del boleto."
                }, status=status.HTTP_400_BAD_REQUEST)
        except BoletoImportado.DoesNotExist:
            return Response({"error": "Boleto no encontrado."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class BoletoMassActionAPIView(APIView):
    """
    Asignación masiva de cliente a boletos huérfanos y facturación.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        boleto_ids = request.data.get('boleto_ids', [])
        cliente_id = request.data.get('cliente_id')
        
        if not boleto_ids or not cliente_id:
            return Response({"error": "Faltan boleto_ids o cliente_id"}, status=400)
            
        try:
            cliente = Cliente.objects.get(pk=cliente_id)
            queryset = BoletoImportado.objects.filter(pk__in=boleto_ids)
            results = InvoiceService.mass_assign_and_invoice(queryset, cliente)
            return Response(results, status=200)
        except Cliente.DoesNotExist:
            return Response({"error": "Cliente no encontrado"}, status=404)
        except Exception as e:
            return Response({"error": str(e)}, status=500)

class VentaDoubleInvoiceAPIView(APIView):
    """
    Genera doble facturación para una venta específica.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            venta = Venta.objects.get(pk=pk)
            f_tercero, f_propia = InvoiceService.generate_double_invoice(venta)
            return Response({
                "factura_tercero": f_tercero.pk if f_tercero else None,
                "factura_propia": f_propia.pk if f_propia else None,
                "mensaje": "Facturación generada con éxito"
            }, status=200)
        except Venta.DoesNotExist:
            return Response({"error": "Venta no encontrada"}, status=404)
        except Exception as e:
            return Response({"error": str(e)}, status=500)

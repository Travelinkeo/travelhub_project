# Archivo: core/views/boleto_views.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from django.core.files.base import ContentFile
import os
import logging
from ..utils.celery_utils import safe_delay

# Importar el servicio de parseo y los modelos de Django
from ..services.ticket_parser_service import orquestar_parseo_de_boleto, generar_pdf_en_memoria
from ..services.venta_automation import VentaAutomationService # AUTOMATION NIVEL 4
from ..services.audit_service import audit_service
from apps.finance.services.invoice_service import InvoiceService
from apps.bookings.models import BoletoImportado, Venta
from apps.crm.models import Cliente

from django.conf import settings

# Throttling
from ..throttling import AgenciaAIParserThrottle, AIParserDailyQuotaThrottle

logger = logging.getLogger(__name__)

class BoletoUploadAPIView(APIView):
    """
    Endpoint para subir un archivo de boleto (PDF/TXT), parsearlo
    de forma inteligente (IA con fallback a Regex) y guardar los
    resultados en la base de datos.
    """
    parser_classes = (MultiPartParser, FormParser)
    permission_classes = [IsAuthenticated]
    throttle_classes = [AgenciaAIParserThrottle, AIParserDailyQuotaThrottle]

    def post(self, request, *args, **kwargs):
        logger.info("-> BoletoUploadAPIView.post() - ASYNC MODE ACTIVATED")
        
        archivo_subido = request.FILES.get('boleto_file')
        if not archivo_subido:
            logger.warning("Intento de subida sin archivo.")
            return Response(
                {"error": "No se proporcionó ningún archivo en el campo 'boleto_file'."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 1. Obtener Agencia del usuario
        agencia_usuario = None
        if hasattr(request.user, 'agencias'):
            usuario_agencia = request.user.agencias.filter(activo=True).first()
            if usuario_agencia:
                agencia_usuario = usuario_agencia.agencia
        
        if not agencia_usuario:
            from core.models import Agencia
            agencia_usuario = Agencia.objects.filter(pk=1).first() or Agencia.objects.first()

        # 2. Crear el registro en estado 'PRO' (Procesando)
        try:
            boleto_importado = BoletoImportado.objects.create(
                archivo_boleto=archivo_subido,
                agencia=agencia_usuario,
                estado_parseo='PRO',
                log_parseo="Enviado a cola de procesamiento asíncrono (Celery)."
            )
            
            # 3. Lanzar la tarea de forma segura (ASISTENCIA DE CARRIL)
            from ..tasks import parsear_boleto_individual
            task = safe_delay(parsear_boleto_individual, boleto_importado.id_boleto_importado)
            
            if task:
                logger.info(f"✅ Boleto {boleto_importado.pk} encolado. TaskID: {task.id}")
                return Response(
                    {
                        "mensaje": "Boleto recibido. El procesamiento se realizará en segundo plano.",
                        "id_boleto_importado": boleto_importado.id_boleto_importado,
                        "task_id": task.id,
                        "estado": "PRO"
                    },
                    status=status.HTTP_202_ACCEPTED
                )
            else:
                # 🛡️ DEGRADACIÓN GRACIOSA: El broker está caído pero la DB está viva.
                # Marcamos el boleto como Pendiente (Cola Llena) para reintento automático posterior.
                boleto_importado.estado_parseo = 'QUE'
                boleto_importado.log_parseo = "⚠️ Broker fuera de línea. Guardado en cola local para procesamiento diferido."
                boleto_importado.save(update_fields=['estado_parseo', 'log_parseo'])
                
                logger.warning(f"🛡️ ASISTENCIA DE CARRIL: Boleto {boleto_importado.pk} en espera por falla de infraestructura.")
                
                return Response(
                    {
                        "mensaje": "Boleto guardado. El procesamiento iniciará automáticamente en unos minutos (Cola diferida).",
                        "id_boleto_importado": boleto_importado.id_boleto_importado,
                        "estado": "QUE"
                    },
                    status=status.HTTP_202_ACCEPTED
                )

        except Exception as e:
            logger.error(f"❌ Error al procesar subida de boleto: {e}")
            return Response(
                {"error": f"Fallo al recibir el archivo: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class BoletoRetryParseAPIView(APIView):
    """
    Fuerza el re-parseo de un boleto importado existente.
    Útil si el primer intento falló o si se ha mejorado el motor de parseo.
    """
    permission_classes = [IsAuthenticated]
    throttle_classes = [AgenciaAIParserThrottle, AIParserDailyQuotaThrottle]

    def post(self, request, pk):
        try:
            from ..services.ticket_parser_service import TicketParserService
            service = TicketParserService()
            
            # El servicio se encarga de re-extraer texto, re-parsear,
            # actualizar campos y re-generar PDF.
            # 🛡️ AI OVERRIDE: Ignoramos datos previos para asegurar limpieza profunda
            resultado = service.procesar_boleto(pk, ignore_manual=True)
            
            if resultado:
                if isinstance(resultado, dict) and resultado.get('status') == 'REVIEW_REQUIRED':
                    return Response({
                        "id": pk,
                        "status": "REVIEW",
                        "error": "Requiere revisión manual (Identidad faltante o baja confianza)."
                    }, status=status.HTTP_200_OK)

                return Response({
                    "mensaje": "Boleto re-procesado con éxito.",
                    "id_boleto_importado": pk,
                    "status": "SUCCESS"
                }, status=status.HTTP_200_OK)
            else:
                # Si el resultado es None, el error detallado debería estar en el log_parseo del boleto
                try:
                    boleto = BoletoImportado.objects.get(pk=pk)
                    error_msg = boleto.log_parseo or "El re-procesamiento falló sin dejar log."
                except:
                    error_msg = "Error desconocido durante el re-procesamiento."
                
                return Response({
                    "error": error_msg
                }, status=status.HTTP_400_BAD_REQUEST)

        except BoletoImportado.DoesNotExist:
            return Response({"error": "Boleto no encontrado."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.exception(f"Error fatal en re-procesamiento de boleto {pk}")
            return Response({"error": f"Fallo Crítico: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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
    Genera dos facturas (Intermediación + Agencia) para una venta.
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

class BoletoAuditAPIView(APIView):
    """
    Endpoint para auditar manualmente los datos de un boleto (útil para carga manual).
    """
    permission_classes = [IsAuthenticated]
    throttle_classes = [AgenciaAIParserThrottle, AIParserDailyQuotaThrottle]

    def post(self, request):
        ticket_data = request.data.get('ticket_data')
        if not ticket_data:
            return Response({"error": "Faltan datos del boleto para auditar."}, status=400)
        
        try:
            auditoria = audit_service.audit_ticket_data(ticket_data)
            return Response(auditoria, status=200)
        except Exception as e:
            return Response({"error": str(e)}, status=500)

class BoletoDeleteAPIView(APIView):
    """
    Elimina un registro de boleto importado.
    """
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        try:
            # Usamos all_objects para permitir borrar incluso si ya estaba soft-deleted
            boleto = BoletoImportado.all_objects.get(pk=pk)
            
            # Verificar si se solicita eliminación física
            physical = request.query_params.get('physical', 'false').lower() == 'true'
            
            if physical:
                # Si hay una venta asociada, intentamos borrarla también si es huérfana
                # o al menos desvincularla. Pero el usuario pidió borrar TODO.
                boleto.delete(force=True)
            else:
                boleto.delete()
                
            return Response({"mensaje": f"Boleto eliminado {'físicamente ' if physical else ''}con éxito"}, status=status.HTTP_204_NO_CONTENT)
        except BoletoImportado.DoesNotExist:
            return Response({"error": "Boleto no encontrado"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

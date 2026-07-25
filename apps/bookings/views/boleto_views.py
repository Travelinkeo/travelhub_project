# Archivo: apps/bookings/views/boleto_views.py

"""Vistas (views) de la aplicación bookings.
"""

import logging
import uuid

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.bookings.models import BoletoImportado, Venta
from apps.common.services.audit_service import audit_service
from apps.common.utils.celery_utils import safe_delay
from apps.crm.models import Cliente

# Importar el servicio de parseo y los modelos de Django
# Throttling
from core.api import AgenciaAIParserThrottle, AIParserDailyQuotaThrottle, get_agencia_from_request
from core.auth_helpers import InternalAPIAuthMixin

logger = logging.getLogger(__name__)


@extend_schema(
    description="Subir un archivo de boleto (PDF/TXT) para parseo con IA + Regex. Retorna ID para consultar estado.",
    request={
        "multipart/form-data": {
            "schema": {
                "type": "object",
                "properties": {
                    "boleto_file": {
                        "type": "string",
                        "format": "binary",
                        "description": "Archivo PDF o TXT del boleto",
                    },
                },
                "required": ["boleto_file"],
            }
        }
    },
    responses={
        202: {"description": "Boleto recibido y encolado para procesamiento asíncrono"},
        400: {"description": "Error en la solicitud (sin archivo o sin agencia)"},
    },
    tags=["Boletos"],
)
class BoletoUploadAPIView(InternalAPIAuthMixin, APIView):
    """
    Endpoint para subir un archivo de boleto (PDF/TXT), parsearlo
    de forma inteligente (IA con fallback a Regex) y guardar los
    resultados en la base de datos.
    """

    parser_classes = (MultiPartParser, FormParser)
    permission_classes = [IsAuthenticated]
    throttle_classes = [AgenciaAIParserThrottle, AIParserDailyQuotaThrottle]

    def post(self, request, *args, **kwargs):
        # post: Post. Args: según implementación. Returns: según implementación.
        logger.info("-> BoletoUploadAPIView.post() - ASYNC MODE ACTIVATED")

        archivo_subido = request.FILES.get("boleto_file")
        if not archivo_subido:
            logger.warning("Intento de subida sin archivo.")
            return Response(
                {"error": "No se proporcionó ningún archivo en el campo 'boleto_file'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 1. Obtener Agencia del usuario
        agencia_usuario = get_agencia_from_request(request)

        # 2. Crear el registro en estado 'PRO' (Procesando)
        try:
            boleto_importado = BoletoImportado.objects.create(
                archivo_boleto=archivo_subido,
                agencia=agencia_usuario,
                estado_parseo="PRO",
                log_parseo="Iniciando procesamiento...",
            )

            # Detectar si Celery está disponible
            from apps.common.utils.celery_utils import _is_celery_available

            celery_ok = _is_celery_available()

            if celery_ok:
                # MODO ASYNC: Encolar en Celery (producción con guarda on_commit)
                from django.db import transaction

                from core.api import parsear_boleto_individual

                b_id = boleto_importado.id_boleto_importado
                transaction.on_commit(lambda: safe_delay(parsear_boleto_individual, b_id))
                logger.info(
                    f"✅ Boleto {boleto_importado.pk} preparado para encolar en Celery (on_commit)."
                )
                return Response(
                    {
                        "mensaje": "Boleto recibido. El procesamiento se realizará en segundo plano.",
                        "id_boleto_importado": boleto_importado.id_boleto_importado,
                        "estado": "PRO",
                    },
                    status=status.HTTP_202_ACCEPTED,
                )

            # MODO SYNC: Procesar inline (desarrollo / Celery offline)
            logger.info(f"⚡ [SYNC MODE] Procesando boleto {boleto_importado.pk} síncronamente...")
            from core.api import parsear_boleto_individual

            parsear_boleto_individual.apply(args=[boleto_importado.id_boleto_importado])

            boleto_importado.refresh_from_db()
            return Response(
                {
                    "mensaje": "Boleto procesado exitosamente.",
                    "id_boleto_importado": boleto_importado.id_boleto_importado,
                    "estado": boleto_importado.estado_parseo,
                    "pdf_url": boleto_importado.get_pdf_url(),
                },
                status=status.HTTP_201_CREATED,
            )

        except Exception:
            error_id = uuid.uuid4().hex[:8].upper()
            logger.exception(f"[{error_id}] Error al procesar subida de boleto")
            return Response(
                {"error": f"Error interno al procesar el archivo. Referencia: TH-{error_id}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


@extend_schema(
    description="Fuerza el re-parseo de un boleto existente. Útil si el primer intento falló o el motor de parseo mejoró.",
    parameters=[
        {
            "name": "pk",
            "in": "path",
            "required": True,
            "schema": {"type": "integer"},
            "description": "ID del boleto a re-parsear",
        },
    ],
    responses={
        202: {"description": "Re-parseo iniciado"},
        404: {"description": "Boleto no encontrado"},
    },
    tags=["Boletos"],
)
class BoletoRetryParseAPIView(InternalAPIAuthMixin, APIView):
    """
    Fuerza el re-parseo de un boleto importado existente.
    Útil si el primer intento falló o si se ha mejorado el motor de parseo.
    """

    permission_classes = [IsAuthenticated]
    throttle_classes = [AgenciaAIParserThrottle, AIParserDailyQuotaThrottle]

    def post(self, request, pk):
        # post: Post. Args: según implementación. Returns: según implementación.
        try:
            # 🔒 P0-002 FIX: Verificación explícita de tenant para prevenir IDOR
            from core.api import get_agencia_from_request, get_object_tenant_or_404

            agencia = get_agencia_from_request(request)
            boleto = get_object_tenant_or_404(
                BoletoImportado.all_objects.select_related("agencia", "proveedor"),
                agencia,
                pk=pk,
            )

            # Detectar si Celery está disponible para elegir modo de procesamiento
            from apps.common.utils.celery_utils import _is_celery_available

            celery_ok = _is_celery_available()

            if celery_ok:
                # MODO ASYNC: Encolar en Celery (producción)
                from core.api import parsear_boleto_individual

                boleto.estado_parseo = "PRO"
                if boleto.archivo_pdf_generado:
                    try:
                        boleto.archivo_pdf_generado.delete(save=False)
                    except Exception as e_del:
                        logger.warning(f"No se pudo borrar archivo físico del PDF: {e_del}")
                boleto.archivo_pdf_generado = None
                boleto.save(update_fields=["estado_parseo", "archivo_pdf_generado"])
                task_id = safe_delay(
                    parsear_boleto_individual, pk, ignore_manual=True, bypass_cache=True
                )
                if task_id:
                    return Response({"status": "PROCESSING", "task_id": str(task_id)}, status=202)
                return Response({"status": "QUEUED"}, status=202)
            else:
                # MODO SYNC: Procesar inline (desarrollo / Celery offline)
                logger.info(f"⚡ [SYNC MODE] Re-procesando boleto {pk} síncronamente...")
                boleto.estado_parseo = "PRO"
                boleto.archivo_pdf_generado = None  # Limpiar PDF anterior para regenerar
                boleto.save(update_fields=["estado_parseo", "archivo_pdf_generado"])

                from core.api import parsear_boleto_individual

                parsear_boleto_individual.apply(
                    args=[pk], kwargs={"ignore_manual": True, "bypass_cache": True}
                )

                boleto.refresh_from_db()
                return Response(
                    {
                        "status": "COMPLETED",
                        "estado_parseo": boleto.estado_parseo,
                        "pdf_url": boleto.get_pdf_url(),
                        "log": str(boleto.log_parseo or "")[:200],
                    },
                    status=200,
                )

        except BoletoImportado.DoesNotExist:
            return Response({"error": "Boleto no encontrado."}, status=status.HTTP_404_NOT_FOUND)
        except Exception:
            error_id = uuid.uuid4().hex[:8].upper()
            logger.exception(f"[{error_id}] Error fatal en re-procesamiento de boleto {pk}")
            return Response(
                {"error": f"Error interno al re-procesar boleto. Referencia: TH-{error_id}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


@extend_schema(
    description="Asignación masiva de cliente a boletos huérfanos y facturación en lote.",
    request={
        "application/json": {
            "schema": {
                "type": "object",
                "properties": {
                    "boleto_ids": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "IDs de los boletos a facturar",
                    },
                    "cliente_id": {"type": "integer", "description": "ID del cliente a asignar"},
                },
                "required": ["boleto_ids", "cliente_id"],
            }
        }
    },
    responses={
        202: {"description": "Facturación masiva encolada para procesamiento asíncrono"},
        200: {"description": "Procesamiento completado síncronamente (fallback)"},
        400: {"description": "Error en la solicitud"},
    },
    tags=["Boletos"],
)
class BoletoMassActionAPIView(InternalAPIAuthMixin, APIView):
    """
    Asignación masiva de cliente a boletos huérfanos y facturación.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        # post: Post. Args: según implementación. Returns: según implementación.
        boleto_ids = request.data.get("boleto_ids", [])
        cliente_id = request.data.get("cliente_id")

        if not boleto_ids or not cliente_id:
            return Response({"error": "Faltan boleto_ids o cliente_id"}, status=400)

        # 1. Obtener Agencia del usuario para aislamiento multi-tenant
        agencia_usuario = get_agencia_from_request(request)

        try:
            Cliente.objects.select_related("agencia").get(pk=cliente_id)

            # Encolar la facturación de forma asíncrona (Job Ingestion API)
            from apps.common.utils.celery_utils import safe_delay
            from core.api import procesar_facturacion_masiva_task

            # Pasamos agency_id para garantizar aislamiento SaaS en el worker Celery
            task_id = safe_delay(
                procesar_facturacion_masiva_task,
                boleto_ids,
                cliente_id,
                agency_id=agencia_usuario.id,
            )

            if task_id:
                logger.info(f"✅ Facturación masiva encolada con éxito. TaskID: {task_id}")
                return Response(
                    {
                        "mensaje": "Facturación masiva encolada con éxito. El procesamiento se realizará en segundo plano.",
                        "task_id": task_id,
                        "status": "QUEUED",
                    },
                    status=status.HTTP_202_ACCEPTED,
                )
            else:
                # Fallback síncrono si el broker no está disponible (Carril de Asistencia)
                logger.warning(
                    "⚠️ Broker Celery no disponible para facturación masiva. Ejecutando síncronamente."
                )
                task_res = procesar_facturacion_masiva_task.apply(
                    args=[boleto_ids, cliente_id], kwargs={"agency_id": agencia_usuario.id}
                )
                results = task_res.result
                return Response(
                    {
                        "mensaje": "Procesamiento completado síncronamente debido a indisponibilidad de cola.",
                        "results": results,
                        "status": "COMPLETED_SYNC",
                    },
                    status=status.HTTP_200_OK,
                )

        except Cliente.DoesNotExist:
            return Response({"error": "Cliente no encontrado"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.exception("Error crítico en BoletoMassActionAPIView")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    description="Genera dos facturas (Intermediación + Agencia) para una venta, según normativa VEN-NIF.",
    parameters=[
        {
            "name": "pk",
            "in": "path",
            "required": True,
            "schema": {"type": "integer"},
            "description": "ID de la venta a facturar",
        },
    ],
    responses={
        200: {
            "description": "Facturación generada con éxito",
            "schema": {
                "type": "object",
                "properties": {
                    "factura_tercero": {"type": "integer"},
                    "factura_propia": {"type": "integer"},
                    "mensaje": {"type": "string"},
                },
            },
        },
        404: {"description": "Venta no encontrada"},
    },
    tags=["Facturación"],
)
class VentaDoubleInvoiceAPIView(InternalAPIAuthMixin, APIView):
    """
    Genera dos facturas (Intermediación + Agencia) para una venta.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        # post: Post. Args: según implementación. Returns: según implementación.
        try:
            from apps.finance.services.invoice_service import InvoiceService

            # 🔒 P0-003 FIX: Verificación explícita de tenant para prevenir IDOR en Ventas
            from core.api import get_agencia_from_request, get_object_tenant_or_404

            agencia = get_agencia_from_request(request)
            venta = get_object_tenant_or_404(Venta, agencia, pk=pk)
            f_tercero, f_propia = InvoiceService.generate_double_invoice(venta)
            return Response(
                {
                    "factura_tercero": f_tercero.pk if f_tercero else None,
                    "factura_propia": f_propia.pk if f_propia else None,
                    "mensaje": "Facturación generada con éxito",
                },
                status=200,
            )
        except Venta.DoesNotExist:
            return Response({"error": "Venta no encontrada"}, status=404)
        except Exception:
            error_id = uuid.uuid4().hex[:8].upper()
            logger.exception(f"[{error_id}] Error en VentaDoubleInvoiceAPIView pk={pk}")
            return Response(
                {"error": f"Error interno al generar facturas. Referencia: TH-{error_id}"},
                status=500,
            )


@extend_schema(
    description="Auditar manualmente los datos extraídos de un boleto. Retorna validación de consistencia de montos.",
    request={
        "application/json": {
            "schema": {
                "type": "object",
                "properties": {
                    "ticket_data": {"type": "object", "description": "Datos del boleto a auditar"},
                },
                "required": ["ticket_data"],
            }
        }
    },
    responses={
        200: {"description": "Resultado de auditoría con validaciones"},
        400: {"description": "Faltan datos del boleto"},
    },
    tags=["Boletos"],
)
class BoletoAuditAPIView(InternalAPIAuthMixin, APIView):
    """
    Endpoint para auditar manualmente los datos de un boleto (útil para carga manual).
    """

    permission_classes = [IsAuthenticated]
    throttle_classes = [AgenciaAIParserThrottle, AIParserDailyQuotaThrottle]

    def post(self, request):
        # post: Post. Args: según implementación. Returns: según implementación.
        ticket_data = request.data.get("ticket_data")
        if not ticket_data:
            return Response({"error": "Faltan datos del boleto para auditar."}, status=400)

        try:
            auditoria = audit_service.audit_ticket_data(ticket_data)
            return Response(auditoria, status=200)
        except Exception as e:
            return Response({"error": str(e)}, status=500)


@extend_schema(
    description="Elimina un registro de boleto importado (soporta soft-delete y hard-delete físico).",
    parameters=[
        {
            "name": "pk",
            "in": "path",
            "required": True,
            "schema": {"type": "integer"},
            "description": "ID del boleto a eliminar",
        },
        {
            "name": "physical",
            "in": "query",
            "required": False,
            "schema": {"type": "boolean"},
            "description": "Si es true, elimina físicamente en lugar de soft-delete",
        },
    ],
    responses={
        204: {"description": "Boleto eliminado exitosamente"},
        404: {"description": "Boleto no encontrado"},
    },
    tags=["Boletos"],
)
class BoletoDeleteAPIView(InternalAPIAuthMixin, APIView):
    """
    Elimina un registro de boleto importado.
    """

    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        # delete: Elimina el objeto de la base de datos. Args: None. Returns: None.
        try:
            from core.api import get_user_active_agency

            agencia = get_user_active_agency(request.user)
            if not request.user.is_superuser and not agencia:
                return Response(
                    {"error": "No se pudo determinar la agencia"}, status=status.HTTP_403_FORBIDDEN
                )

            boleto = BoletoImportado.all_objects.get(pk=pk)

            if not request.user.is_superuser and boleto.agencia_id != agencia.id:
                return Response({"error": "Boleto no encontrado"}, status=status.HTTP_404_NOT_FOUND)

            physical = request.query_params.get("physical", "false").lower() == "true"

            if physical:
                boleto.hard_delete()
            else:
                boleto.delete()

            return Response(
                {"mensaje": f"Boleto eliminado {'físicamente ' if physical else ''}con éxito"},
                status=status.HTTP_204_NO_CONTENT,
            )
        except BoletoImportado.DoesNotExist:
            return Response({"error": "Boleto no encontrado"}, status=status.HTTP_404_NOT_FOUND)
        except Exception:
            error_id = uuid.uuid4().hex[:8].upper()
            logger.exception(f"[{error_id}] Error en BoletoDeleteAPIView pk={pk}")
            return Response(
                {"error": f"Error interno al eliminar boleto. Referencia: TH-{error_id}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

"""
Boleto Status API View
======================
API endpoint para consultar el estado de procesamiento de un boleto
sin depender de polling del frontend.
"""

import logging

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.bookings.models import BoletoImportado
from core.api import get_agencia_from_request, get_object_tenant_or_404
from core.auth_helpers import InternalAPIAuthMixin

logger = logging.getLogger(__name__)


@extend_schema(
    description="Obtiene el estado actual de procesamiento de un boleto (parseo, PDF, errores).",
    responses={
        200: {
            "description": "Estado del boleto",
            "schema": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "estado_parseo": {
                        "type": "string",
                        "enum": ["PEN", "PRO", "COM", "REV", "ERR", "NAP"],
                    },
                    "estado_display": {"type": "string"},
                    "tiene_pdf": {"type": "boolean"},
                    "pdf_url": {"type": "string", "nullable": True},
                    "log_parseo": {"type": "string", "nullable": True},
                    "fecha_subida": {"type": "string", "format": "date-time"},
                    "updated_at": {"type": "string", "format": "date-time"},
                },
            },
        },
        404: {"description": "Boleto no encontrado"},
    },
    tags=["Boletos"],
)
class BoletoStatusAPIView(InternalAPIAuthMixin, APIView):
    """
    Endpoint para consultar el estado de procesamiento de un boleto.
    Útil para frontends que necesitan polling sin depender de vistas HTML.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        """GET /api/boletos/<pk>/status/"""
        try:
            agencia = get_agencia_from_request(request)
            boleto = get_object_tenant_or_404(
                BoletoImportado.all_objects.select_related("agencia", "venta_asociada"),
                agencia,
                pk=pk,
            )

            # Mapear estado a display legible
            estado_map = {
                "PEN": "Pendiente de Parseo",
                "PRO": "En Proceso",
                "COM": "Parseo Completado",
                "REV": "Revisión Requerida",
                "ERR": "Error en Parseo",
                "NAP": "No Aplica Parseo",
                "QUE": "Pendiente (Cola Llena)",
                "EN_PROCESO": "En Proceso",
            }

            estado = boleto.estado_parseo
            if estado == "EN_PROCESO":
                estado = "PRO"  # Normalizar

            # 🛡️ GUARDA ANTI-ATASCAMIENTO: Si lleva más de 15 segundos en 'PRO', sellar a 'REV'
            if estado == "PRO" and boleto.updated_at:
                from django.utils import timezone

                elaps = (timezone.now() - boleto.updated_at).total_seconds()
                if elaps > 15:
                    logger.warning(
                        f"⚠️ [ANTI-STUCK GUARD] Boleto {pk} atascado en 'PRO' por {elaps:.1f}s. Auto-sellando a REV."
                    )
                    boleto.estado_parseo = BoletoImportado.EstadoParseo.REVISION_REQUERIDA
                    boleto.log_parseo = (
                        boleto.log_parseo or ""
                    ) + "\n[Auto-Guard] Proceso excedió tiempo máximo (15s). Sellado a revisión."
                    boleto.save(update_fields=["estado_parseo", "log_parseo", "updated_at"])
                    estado = "REV"

            return Response(
                {
                    "id": boleto.id_boleto_importado,
                    "estado_parseo": estado,
                    "estado_display": estado_map.get(estado, "Desconocido"),
                    "tiene_pdf": bool(boleto.archivo_pdf_generado),
                    "pdf_url": boleto.get_pdf_url() if boleto.archivo_pdf_generado else None,
                    "log_parseo": boleto.log_parseo,
                    "fecha_subida": boleto.fecha_subida,
                    "updated_at": boleto.updated_at,
                },
                status=status.HTTP_200_OK,
            )

        except BoletoImportado.DoesNotExist:
            return Response(
                {"error": "Boleto no encontrado."},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            error_id = "TH-" + "".join([c for c in str(e) if c.isalnum()])[:8].upper()
            logger.exception(f"[{error_id}] Error en BoletoStatusAPIView pk={pk}")
            return Response(
                {"error": f"Error interno al consultar estado. Referencia: {error_id}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

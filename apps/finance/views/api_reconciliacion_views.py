from decimal import Decimal

from django.db.models import Count, Q, Sum
from django.db.models.functions import Coalesce
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import parsers, status, views, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.finance.models.reconciliacion import ConciliacionBoleto, ReporteReconciliacion
from apps.finance.serializers import ConciliacionBoletoSerializer, ReporteReconciliacionSerializer
from apps.finance.services.smart_reconciliation_service import SmartReconciliationService
from core.api.mixins.tenant import TenantViewSetMixin
from core.auth_helpers import InternalAPIAuthMixin


@extend_schema_view(
    list=extend_schema(description="Listar todos los reportes de reconciliación BSP/Consolidador."),
    retrieve=extend_schema(description="Obtener detalle de un reporte de reconciliación."),
    create=extend_schema(
        description="Subir un nuevo reporte BSP/Consolidador (PDF o Excel) para reconciliación.",
        request={
            "multipart/form-data": {
                "schema": {
                    "type": "object",
                    "properties": {"file": {"type": "string", "format": "binary"}},
                }
            }
        },
    ),
    update=extend_schema(description="Actualizar un reporte de reconciliación."),
    partial_update=extend_schema(description="Actualizar parcialmente un reporte."),
    destroy=extend_schema(description="Eliminar un reporte de reconciliación."),
    process_ai=extend_schema(
        description="Ejecutar el motor de conciliación IA (Gemini) para cruzar boletos del reporte contra la base local.",
        responses={200: {"description": "Cruce IA ejecutado exitosamente"}},
    ),
    conciliaciones=extend_schema(
        description="Obtener el detalle de las líneas cruzadas por la IA para este reporte.",
        responses={200: ConciliacionBoletoSerializer(many=True)},
    ),
)
class ReporteReconciliacionViewSet(InternalAPIAuthMixin, TenantViewSetMixin, viewsets.ModelViewSet):
    """
    ViewSet para manejar CRUD de reportes BSP/Consolidador subidos por la Agencia.
    """

    queryset = ReporteReconciliacion.objects.all().order_by("-fecha_subida")
    serializer_class = ReporteReconciliacionSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [parsers.MultiPartParser, parsers.FormParser]

    @action(detail=True, methods=["post"])
    def process_ai(self, request, pk=None):
        """
        Gatilla manualmente el Servicio IAS de Gemini para extraer y cruzar boletos.
        """
        reporte = self.get_object()
        try:
            SmartReconciliationService.procesar_reporte(reporte.id_reporte)
            reporte.refresh_from_db()
            return Response(
                {
                    "status": "ok",
                    "message": "Cruce IA ejecutado exitosamente.",
                    "report_estado": reporte.estado,
                }
            )
        except Exception as e:
            return Response(
                {"status": "error", "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=["get"])
    def conciliaciones(self, request, pk=None):
        """
        Devuelve el detalle de las líneas cruzadas por la IA contra la base local
        pertenecientes a este reporte.
        """
        reporte = self.get_object()
        conciliaciones = reporte.conciliaciones.all().select_related(
            "linea_reporte", "boleto_local", "sugerencia_asiento"
        )
        serializer = ConciliacionBoletoSerializer(conciliaciones, many=True)
        return Response(serializer.data)


@extend_schema(
    description="Obtener los KPIs principales del tablero de reconciliación (discrepancias, pérdidas, ahorros).",
    responses={200: {"description": "KPIs de reconciliación"}},
)
class ReconciliationDashboardStatsAPIView(InternalAPIAuthMixin, views.APIView):
    """
    Endpoint para devolver los KPIs principales al tablero del Frontend.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = self.request.user
        agencia_id = user.perfil.agencia_id if hasattr(user, "perfil") else None

        base_qs = ConciliacionBoleto.objects.filter(reporte__agencia_id=agencia_id)

        stats = base_qs.aggregate(
            total_discrepancias=Count(
                "id_conciliacion", filter=Q(estado=ConciliacionBoleto.EstadosCruce.DISCREPANCIA)
            ),
            total_huerfanos=Count(
                "id_conciliacion", filter=Q(estado__in=["HUERFANO_PROVEEDOR", "HUERFANO_LOCAL"])
            ),
            perdida_detectada=Coalesce(
                Sum(
                    "diferencia_total",
                    filter=Q(
                        diferencia_total__lt=0, estado=ConciliacionBoleto.EstadosCruce.DISCREPANCIA
                    ),
                ),
                Decimal(0),
            ),
            ahorros_detectados=Coalesce(
                Sum(
                    "diferencia_total",
                    filter=Q(
                        diferencia_total__gt=0, estado=ConciliacionBoleto.EstadosCruce.DISCREPANCIA
                    ),
                ),
                Decimal(0),
            ),
            asientos_generados=Count("id_conciliacion", filter=Q(sugerencia_asiento__isnull=False)),
        )

        return Response(stats)

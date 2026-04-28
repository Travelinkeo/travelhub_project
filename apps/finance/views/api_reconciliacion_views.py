from rest_framework import viewsets, views, status, parsers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Sum, Count, Q
from django.db.models.functions import Coalesce
from decimal import Decimal

from apps.finance.models.reconciliacion import ReporteReconciliacion, ConciliacionBoleto
from apps.finance.serializers import ReporteReconciliacionSerializer, ConciliacionBoletoSerializer
from apps.finance.services.smart_reconciliation_service import SmartReconciliationService

class ReporteReconciliacionViewSet(viewsets.ModelViewSet):
    """
    ViewSet para manejar CRUD de reportes BSP/Consolidador subidos por la Agencia.
    """
    queryset = ReporteReconciliacion.objects.all().order_by('-fecha_subida')
    serializer_class = ReporteReconciliacionSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [parsers.MultiPartParser, parsers.FormParser]

    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'perfil') and user.perfil.agencia_id:
            return self.queryset.filter(agencia_id=user.perfil.agencia_id)
        return self.queryset

    def perform_create(self, serializer):
        user = self.request.user
        agencia = user.perfil.agencia if hasattr(user, 'perfil') else None
        serializer.save(agencia=agencia)

    @action(detail=True, methods=['post'])
    def process_ai(self, request, pk=None):
        """
        Gatilla manualmente el Servicio IAS de Gemini para extraer y cruzar boletos.
        """
        reporte = self.get_object()
        try:
            SmartReconciliationService.procesar_reporte(reporte.id_reporte)
            reporte.refresh_from_db()
            return Response({'status': 'ok', 'message': 'Cruce IA ejecutado exitosamente.', 'report_estado': reporte.estado})
        except Exception as e:
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['get'])
    def conciliaciones(self, request, pk=None):
        """
        Devuelve el detalle de las líneas cruzadas por la IA contra la base local
        pertenecientes a este reporte.
        """
        reporte = self.get_object()
        conciliaciones = reporte.conciliaciones.all().select_related('linea_reporte', 'boleto_local', 'sugerencia_asiento')
        serializer = ConciliacionBoletoSerializer(conciliaciones, many=True)
        return Response(serializer.data)


class ReconciliationDashboardStatsAPIView(views.APIView):
    """
    Endpoint para devolver los KPIs principales al tablero del Frontend en NextJS.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = self.request.user
        agencia_id = user.perfil.agencia_id if hasattr(user, 'perfil') else None

        base_qs = ConciliacionBoleto.objects.filter(reporte__agencia_id=agencia_id)

        stats = base_qs.aggregate(
            total_discrepancias=Count('id_conciliacion', filter=Q(estado=ConciliacionBoleto.EstadosCruce.DISCREPANCIA)),
            total_huerfanos=Count('id_conciliacion', filter=Q(estado__in=['HUERFANO_PROVEEDOR', 'HUERFANO_LOCAL'])),
            perdida_detectada=Coalesce(Sum('diferencia_total', filter=Q(diferencia_total__lt=0, estado=ConciliacionBoleto.EstadosCruce.DISCREPANCIA)), Decimal(0)),
            ahorros_detectados=Coalesce(Sum('diferencia_total', filter=Q(diferencia_total__gt=0, estado=ConciliacionBoleto.EstadosCruce.DISCREPANCIA)), Decimal(0)),
            asientos_generados=Count('id_conciliacion', filter=Q(sugerencia_asiento__isnull=False)),
        )

        return Response(stats)

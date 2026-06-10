"""
ViewSets para las mejoras de boletería
"""

from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.api.mixins.tenant import TenantViewSetMixin
from core.auth_helpers import InternalAPIAuthMixin
from core.models.anulaciones import AnulacionBoleto
from core.models.historial_boletos import HistorialCambioBoleto
from core.serializers_boletos import AnulacionBoletoSerializer, HistorialCambioBoletoSerializer


@extend_schema_view(
    list=extend_schema(description="Listar el historial de cambios de boletos."),
    retrieve=extend_schema(description="Obtener detalle de un cambio en el historial."),
    create=extend_schema(description="Registrar un cambio en el historial de un boleto."),
    update=extend_schema(description="Actualizar un registro del historial."),
    partial_update=extend_schema(description="Actualizar parcialmente un registro."),
    destroy=extend_schema(description="Eliminar un registro del historial."),
)
class HistorialCambioBoletoViewSet(InternalAPIAuthMixin, TenantViewSetMixin, viewsets.ModelViewSet):
    """ViewSet para historial de cambios de boletos"""

    queryset = HistorialCambioBoleto.objects.select_related("boleto", "usuario").all()
    serializer_class = HistorialCambioBoletoSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["boleto", "tipo_cambio", "usuario"]
    search_fields = ["descripcion", "boleto__numero_boleto"]
    ordering = ["-fecha_cambio"]


@extend_schema_view(
    list=extend_schema(description="Listar todas las anulaciones y reembolsos de boletos."),
    retrieve=extend_schema(description="Obtener detalle de una anulación."),
    create=extend_schema(description="Crear una solicitud de anulación."),
    update=extend_schema(description="Actualizar una solicitud de anulación."),
    partial_update=extend_schema(description="Actualizar parcialmente una anulación."),
    destroy=extend_schema(description="Eliminar un registro de anulación."),
    aprobar=extend_schema(
        description="Aprobar una solicitud de anulación pendiente.",
        responses={200: AnulacionBoletoSerializer},
    ),
    rechazar=extend_schema(
        description="Rechazar una solicitud de anulación.",
        request={
            "application/json": {
                "schema": {"type": "object", "properties": {"motivo_rechazo": {"type": "string"}}}
            }
        },
        responses={200: AnulacionBoletoSerializer},
    ),
    marcar_reembolsada=extend_schema(
        description="Marcar una anulación aprobada como reembolsada.",
        responses={200: AnulacionBoletoSerializer},
    ),
)
class AnulacionBoletoViewSet(InternalAPIAuthMixin, TenantViewSetMixin, viewsets.ModelViewSet):
    """ViewSet para anulaciones y reembolsos"""

    queryset = AnulacionBoleto.objects.select_related(
        "boleto", "solicitado_por", "aprobado_por"
    ).all()
    serializer_class = AnulacionBoletoSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["boleto", "tipo_anulacion", "estado", "solicitado_por"]
    search_fields = ["motivo", "boleto__numero_boleto"]
    ordering = ["-fecha_solicitud"]

    @action(detail=True, methods=["post"])
    def aprobar(self, request, pk=None):
        """Aprobar una anulación"""
        from django.utils import timezone

        anulacion = self.get_object()
        if anulacion.estado != "SOL":
            return Response({"error": "Solo se pueden aprobar anulaciones solicitadas"}, status=400)

        anulacion.estado = "APR"
        anulacion.aprobado_por = request.user
        anulacion.fecha_aprobacion = timezone.now()
        anulacion.save()

        serializer = self.get_serializer(anulacion)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def rechazar(self, request, pk=None):
        """Rechazar una anulación"""
        anulacion = self.get_object()
        if anulacion.estado != "SOL":
            return Response(
                {"error": "Solo se pueden rechazar anulaciones solicitadas"}, status=400
            )

        anulacion.estado = "REC"
        anulacion.aprobado_por = request.user
        anulacion.notas = request.data.get("motivo_rechazo", "")
        anulacion.save()

        serializer = self.get_serializer(anulacion)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def marcar_reembolsada(self, request, pk=None):
        """Marcar como reembolsada"""
        from django.utils import timezone

        anulacion = self.get_object()
        if anulacion.estado != "APR":
            return Response(
                {"error": "Solo se pueden reembolsar anulaciones aprobadas"}, status=400
            )

        anulacion.estado = "REE"
        anulacion.fecha_reembolso = timezone.now()
        anulacion.save()

        serializer = self.get_serializer(anulacion)
        return Response(serializer.data)

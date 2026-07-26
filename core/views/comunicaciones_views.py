# core/views/comunicaciones_views.py
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.communications.models import ComunicacionProveedor
from core.api.mixins.tenant import TenantViewSetMixin
from core.auth_helpers import InternalAPIAuthMixin
from core.serializers import ComunicacionProveedorSerializer


@extend_schema_view(
    list=extend_schema(
        description="Listar todas las comunicaciones con proveedores (filtrables por categoría, remitente)."
    ),
    retrieve=extend_schema(description="Obtener detalle de una comunicación."),
    por_categoria=extend_schema(description="Agrupa y cuenta comunicaciones por categoría."),
    recientes=extend_schema(
        description="Obtener las últimas 20 comunicaciones.",
        responses={200: ComunicacionProveedorSerializer(many=True)},
    ),
)
class ComunicacionProveedorViewSet(
    TenantViewSetMixin, InternalAPIAuthMixin, viewsets.ReadOnlyModelViewSet
):
    """ComunicacionProveedorViewSet."""

    queryset = ComunicacionProveedor.objects.all().order_by("-fecha_recepcion")
    serializer_class = ComunicacionProveedorSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["categoria", "remitente"]
    search_fields = ["asunto", "remitente", "cuerpo_completo", "contenido_extraido"]
    ordering_fields = ["fecha_recepcion"]
    ordering = ["-fecha_recepcion"]

    @action(detail=False, methods=["get"])
    def por_categoria(self, request):
        """Agrupa comunicaciones por categoría"""
        from django.db.models import Count

        categorias = (
            self.queryset.values("categoria").annotate(count=Count("id")).order_by("-count")
        )

        return Response(list(categorias))

    @action(detail=False, methods=["get"])
    def recientes(self, request):
        """Últimas 20 comunicaciones"""
        comunicaciones = self.queryset[:20]
        serializer = self.get_serializer(comunicaciones, many=True)
        return Response(serializer.data)

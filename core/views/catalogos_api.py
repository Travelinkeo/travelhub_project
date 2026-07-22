from rest_framework import filters, permissions, viewsets

from apps.bookings.models import ComisionProveedorServicio
from core.api.mixins.tenant import TenantViewSetMixin
from core.auth_helpers import InternalAPIAuthMixin
from core.serializers import ComisionProveedorServicioSerializer


class ComisionProveedorServicioViewSet(
    InternalAPIAuthMixin, TenantViewSetMixin, viewsets.ModelViewSet
):
    """
    API endpoint para gestionar las reglas de comisiones de proveedores.
    """

    queryset = ComisionProveedorServicio.objects.all().select_related("proveedor", "moneda")
    serializer_class = ComisionProveedorServicioSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None
    filter_backends = [filters.SearchFilter]
    search_fields = ["proveedor__nombre", "tipo_servicio"]

    def get_queryset(self):
        queryset = super().get_queryset()
        proveedor_id = self.request.query_params.get("proveedor", None)
        if proveedor_id:
            queryset = queryset.filter(proveedor_id=proveedor_id)
        return queryset

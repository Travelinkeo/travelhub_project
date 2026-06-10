# core/views/liquidacion_views.py
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.contabilidad.models import ItemLiquidacion, LiquidacionProveedor
from core.api.mixins.tenant import TenantViewSetMixin
from core.auth_helpers import InternalAPIAuthMixin
from core.serializers import ItemLiquidacionSerializer, LiquidacionProveedorSerializer
from core.throttling import LiquidacionRateThrottle


@extend_schema_view(
    list=extend_schema(
        description="Listar todas las liquidaciones a proveedores (con paginación, filtros y búsqueda)."
    ),
    retrieve=extend_schema(description="Obtener detalle de una liquidación específica."),
    create=extend_schema(description="Crear una nueva liquidación a proveedor."),
    update=extend_schema(description="Actualizar completamente una liquidación."),
    partial_update=extend_schema(description="Actualizar parcialmente una liquidación."),
    destroy=extend_schema(description="Eliminar una liquidación."),
    marcar_pagada=extend_schema(
        description="Marca una liquidación como completamente pagada.",
        responses={200: {"description": "Liquidación marcada como pagada"}},
    ),
    registrar_pago_parcial=extend_schema(
        description="Registra un pago parcial a una liquidación.",
        request={
            "application/json": {
                "schema": {
                    "type": "object",
                    "properties": {
                        "monto": {"type": "number", "description": "Monto del pago parcial"}
                    },
                    "required": ["monto"],
                }
            }
        },
        responses={
            200: {"description": "Pago registrado exitosamente"},
            400: {"description": "Error: monto requerido o excede saldo pendiente"},
        },
    ),
    pendientes=extend_schema(
        description="Obtener todas las liquidaciones pendientes de pago.",
        responses={200: LiquidacionProveedorSerializer(many=True)},
    ),
    por_proveedor=extend_schema(
        description="Filtrar liquidaciones por proveedor específico.",
        parameters=[],
        responses={200: LiquidacionProveedorSerializer(many=True)},
    ),
)
class LiquidacionProveedorViewSet(InternalAPIAuthMixin, TenantViewSetMixin, viewsets.ModelViewSet):
    queryset = LiquidacionProveedor.objects.all().select_related("proveedor", "venta")
    serializer_class = LiquidacionProveedorSerializer
    permission_classes = [IsAuthenticated]
    throttle_classes = [LiquidacionRateThrottle]
    filterset_fields = ["estado", "proveedor", "venta"]
    search_fields = ["id_liquidacion", "proveedor__nombre", "venta__localizador"]
    ordering_fields = ["fecha_emision", "monto_total", "saldo_pendiente"]
    ordering = ["-fecha_emision"]

    @action(detail=True, methods=["post"])
    def marcar_pagada(self, request, pk=None):
        liquidacion = self.get_object()
        liquidacion.monto_pagado = liquidacion.monto_total
        liquidacion.estado = "PAG"
        liquidacion.save()
        return Response({"status": "Liquidación marcada como pagada"})

    @action(detail=True, methods=["post"])
    def registrar_pago_parcial(self, request, pk=None):
        from decimal import Decimal

        liquidacion = self.get_object()
        monto = request.data.get("monto")

        if not monto:
            return Response({"error": "Monto requerido"}, status=status.HTTP_400_BAD_REQUEST)

        monto = Decimal(str(monto))
        if monto > liquidacion.saldo_pendiente:
            return Response(
                {"error": "Monto excede saldo pendiente"}, status=status.HTTP_400_BAD_REQUEST
            )

        liquidacion.monto_pagado += monto
        liquidacion.save()

        return Response(
            {
                "status": "Pago registrado",
                "saldo_pendiente": float(liquidacion.saldo_pendiente),
                "estado": liquidacion.estado,
            }
        )

    @action(detail=False, methods=["get"])
    def pendientes(self, request):
        liquidaciones = self.queryset.filter(estado="PEN")
        serializer = self.get_serializer(liquidaciones, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def por_proveedor(self, request):
        proveedor_id = request.query_params.get("proveedor_id")
        if not proveedor_id:
            return Response({"error": "proveedor_id requerido"}, status=status.HTTP_400_BAD_REQUEST)

        liquidaciones = self.queryset.filter(proveedor_id=proveedor_id)
        serializer = self.get_serializer(liquidaciones, many=True)
        return Response(serializer.data)


@extend_schema_view(
    list=extend_schema(description="Listar todos los items de liquidación."),
    retrieve=extend_schema(description="Obtener detalle de un item de liquidación."),
)
class ItemLiquidacionViewSet(
    InternalAPIAuthMixin, TenantViewSetMixin, viewsets.ReadOnlyModelViewSet
):
    queryset = ItemLiquidacion.objects.all().select_related("liquidacion", "item_venta")
    serializer_class = ItemLiquidacionSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["liquidacion"]

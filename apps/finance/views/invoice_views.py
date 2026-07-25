"""Vistas (views) de la aplicación finance.
"""

import logging
import uuid

from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import filters, serializers, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.bookings.models import Venta
from apps.finance.models import Factura
from apps.finance.serializers import FacturaSerializer
from apps.finance.services.invoice_service import InvoiceService
from core.api.mixins.tenant import TenantViewSetMixin
from core.auth_helpers import InternalAPIAuthMixin

logger = logging.getLogger(__name__)


class VentaDoubleInvoiceAPIView(InternalAPIAuthMixin, APIView):
    """
    Genera dos facturas (Intermediación + Agencia) para una venta.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Generar doble factura para Venta",
        description="Genera la factura de intermediación (tercero) y la propia (agencia).",
        responses={
            200: inline_serializer(
                name="DoubleInvoiceResponse",
                fields={
                    "factura_tercero": serializers.IntegerField(allow_null=True),
                    "factura_propia": serializers.IntegerField(allow_null=True),
                    "mensaje": serializers.CharField(),
                },
            )
        },
    )
    def post(self, request, pk):
        # post: Post. Args: según implementación. Returns: según implementación.
        try:
            # P0-003 FIX: Verificación explícita de tenant para prevenir IDOR en Ventas.
            # Devuelve 404 (no 403) si la venta no pertenece a la agencia, para no
            # revelar que el objeto existe en otra agencia.
            from core.api import get_agencia_from_request, get_object_tenant_or_404

            agencia = get_agencia_from_request(request)
            venta = get_object_tenant_or_404(
                Venta.objects.select_related("cliente", "agencia", "moneda"),
                agencia,
                pk=pk,
            )
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
            # P0-006 FIX: No exponer str(e). Log con error_id y mensaje genérico al cliente.
            error_id = uuid.uuid4().hex[:8].upper()
            logger.exception(f"[{error_id}] Error en VentaDoubleInvoiceAPIView pk={pk}")
            return Response(
                {"error": f"Error interno al generar facturas. Referencia: TH-{error_id}"},
                status=500,
            )


class FacturaViewSet:
    """Clase FacturaViewSet. Uso: según contexto de la aplicación.
    """
    queryset = (
        Factura.objects.select_related("cliente")
        .prefetch_related("items")
        .order_by("-fecha_emision")
    )
    serializer_class = FacturaSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = [
        "numero_control",
        "cliente__nombres",
        "cliente__apellidos",
        "cliente__nombre_empresa",
    ]

    def list(self, request, *args, **kwargs):
        # list: Lista . Args: filtros. Returns: listado.
        logger.info("FacturaViewSet.list() called")
        return super().list(request, *args, **kwargs)

    def perform_create(self, serializer):
        # perform_create: Perform create. Args: según implementación. Returns: según implementación.
        serializer.save()

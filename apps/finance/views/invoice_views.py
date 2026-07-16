import logging

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
        try:
            venta = Venta.objects.select_related("cliente", "agencia", "moneda").get(pk=pk)
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
        except Exception as e:
            return Response({"error": str(e)}, status=500)


class FacturaViewSet(TenantViewSetMixin, viewsets.ModelViewSet):
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
        logger.info("FacturaViewSet.list() called")
        return super().list(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save()

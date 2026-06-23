import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST
from django.views.generic import ListView, View
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import filters, serializers, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.bookings.models import Venta
from apps.bookings.models.venta import ItemVenta
from apps.finance.models.core_finance import Factura
from apps.finance.models.facturas_proveedores import FacturaProveedor
from apps.finance.serializers import FacturaSerializer
from apps.finance.services.invoice_matcher_service import InvoiceMatcherService
from apps.finance.services.invoice_service import InvoiceService
from core.api import AuditLog, crear_audit_log
from core.api.mixins.tenant import TenantViewSetMixin
from core.auth_helpers import InternalAPIAuthMixin

logger = logging.getLogger(__name__)


class InvoiceReviewDashboardView(LoginRequiredMixin, ListView):
    """
    Vista espectacular para que el contador resuelva facturas en REV_MAN.
    Diseño Split-screen con visor de PDF y sugerencias de matching.
    """

    model = FacturaProveedor
    template_name = "finance/invoice_review_dashboard.html"
    context_object_name = "facturas_pendientes"

    def get_queryset(self):
        # Filtramos por Agencia (via middleware/SAAS manager) y estado REQUIERE_REVISION
        return (
            FacturaProveedor.objects.filter(
                agencia_id=self.request.agencia.id,
                estado=FacturaProveedor.EstadoFactura.REQUIERE_REVISION,
            )
            .select_related("moneda")
            .order_by("-fecha_registro")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Pre-calcular matches delegando la lógica al Servicio
        facturas_con_matches = []
        for factura in context["facturas_pendientes"]:
            matches = InvoiceMatcherService.get_potential_matches_for_invoice(factura)
            facturas_con_matches.append({"factura": factura, "matches": matches})

        context["facturas_con_matches"] = facturas_con_matches
        return context


class MatchInvoiceActionView(LoginRequiredMixin, View):
    """
    Endpoint HTMX para realizar el vínculo manual.
    """

    def post(self, request, factura_id, item_id):
        factura = get_object_or_404(FacturaProveedor, pk=factura_id, agencia_id=request.agencia.id)
        item = get_object_or_404(ItemVenta, pk=item_id, agencia_id=request.agencia.id)

        factura.estado = FacturaProveedor.EstadoFactura.CONCILIADA
        factura.proveedor = item.proveedor_servicio
        if not factura.datos_json:
            factura.datos_json = {}
        factura.datos_json["manual_match_item_id"] = item.id_item_venta
        factura.datos_json["conciliated_by"] = request.user.username
        factura.save()

        # Devolvemos un snippet de éxito para eliminar la tarjeta de la vista vía HTMX
        return HttpResponse(f"""
            <div class="p-4 bg-emerald-900/50 border border-emerald-500 text-emerald-200 rounded-lg animate-fade-out">
                ✅ Factura {factura.numero_factura} conciliada con éxito.
            </div>
            <script>
                setTimeout(() => {{ 
                    document.getElementById('factura-row-{factura_id}').remove(); 
                }}, 2000);
            </script>
        """)


@require_POST
def force_match_invoice_htmx(request, factura_id):
    """
    Vista HTMX para forzar la conciliación manual de una factura.
    Garantiza vinculación, cambio de estado y AuditLog forense.
    """
    # Validación de tenant (via middleware request.agencia)
    factura = get_object_or_404(FacturaProveedor, pk=factura_id, agencia_id=request.agencia.id)

    item_id = request.POST.get("item_venta_id")
    if not item_id:
        return HttpResponse("ID de ítem no proporcionado", status=400)

    item = get_object_or_404(ItemVenta, pk=item_id, agencia_id=request.agencia.id)

    # Lógica de vinculación
    factura.estado = FacturaProveedor.EstadoFactura.CONCILIADA
    factura.proveedor = item.proveedor_servicio

    if not factura.datos_json:
        factura.datos_json = {}

    factura.datos_json["manual_match_item_id"] = item.id_item_venta
    factura.datos_json["force_conciliated"] = True
    factura.datos_json["user_id"] = request.user.id
    factura.save()

    # AuditLog de Bóveda de Estado
    crear_audit_log(
        modelo="FacturaProveedor",
        object_id=factura.pk,
        accion=AuditLog.Accion.STATE,
        descripcion=f"Forzó la conciliación manualmente de factura {factura.numero_factura} con ItemVenta {item.id_item_venta}",
        datos_nuevos={"estado": "CONCILIADA", "item_id": item.id_item_venta},
        user=request.user,
        agencia=request.agencia,
    )

    # Respuesta HTMX: Reemplaza la tarjeta entera de la factura
    return HttpResponse(f"""
        <div class="col-span-full p-12 bg-emerald-950/40 border-2 border-emerald-500/30 rounded-[2.5rem] flex flex-col items-center justify-center animate-fade-out shadow-2xl shadow-emerald-500/10">
            <div class="w-24 h-24 bg-emerald-500 rounded-full flex items-center justify-center mb-6 shadow-2xl shadow-emerald-500/40 transition-all duration-500 transform hover:scale-110">
                <svg class="w-12 h-12 text-slate-950" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M5 13l4 4L19 7"></path>
                </svg>
            </div>
            <h4 class="text-3xl font-black text-white uppercase italic tracking-tighter mb-2">¡Conciliada con éxito!</h4>
            <p class="text-emerald-400 font-bold text-lg">La factura {factura.numero_factura} ha sido vinculada correctamente.</p>
            <div class="mt-6 px-4 py-1.5 bg-emerald-500/10 rounded-full text-[10px] text-emerald-500 uppercase font-black tracking-widest border border-emerald-500/20">
                ID Auditoría: {factura.pk}
            </div>
        </div>
        <script>
            setTimeout(() => {{ 
                const el = document.getElementById('factura-row-{factura_id}');
                if (el) {{
                    el.style.opacity = '0';
                    el.style.transform = 'translateY(-20px)';
                    el.style.transition = 'all 0.5s ease';
                    setTimeout(() => el.remove(), 500);
                }}
            }}, 2000);
        </script>
    """)


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
        Factura.objects.select_related("cliente", "moneda", "asiento_contable_factura")
        .prefetch_related("items_factura")
        .order_by("-fecha_emision")
    )
    serializer_class = FacturaSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = [
        "numero_factura",
        "cliente__nombres",
        "cliente__apellidos",
        "cliente__nombre_empresa",
    ]

    def list(self, request, *args, **kwargs):
        logger.info("FacturaViewSet.list() called")
        return super().list(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save()

import logging

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import redirect
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView, ListView

from apps.bookings.models import Venta
from apps.finance.models import Factura
from apps.finance.services.facturacion_service import FacturacionService
from core.api import (
    HtmxResponseMixin,
    SaaSMixin,
    agency_role_required,
    get_agencia_or_403,
    get_object_tenant_or_404,
)

logger = logging.getLogger(__name__)


class FacturacionDashboardView(HtmxResponseMixin, SaaSMixin, LoginRequiredMixin, ListView):
    model = Factura
    template_name = "core/erp/facturacion/dashboard.html"
    htmx_template_name = "finance/partials/factura_list_htmx.html"
    context_object_name = "facturas"
    paginate_by = 20

    def get_queryset(self):
        queryset = (
            super()
            .get_queryset()
            .select_related("cliente", "agencia")
            .prefetch_related("items", "pagos")
            .order_by("-fecha_emision")
        )

        q = self.request.GET.get("q")
        if q:
            queryset = queryset.filter(
                Q(numero_control__icontains=q)
                | Q(cliente__nombres__icontains=q)
                | Q(cliente__apellidos__icontains=q)
                | Q(cliente__numero_documento__icontains=q)
            )

        estado = self.request.GET.get("estado")
        if estado:
            queryset = queryset.filter(estado=estado)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Stats reusing the agency-filtered queryset from SaaSMixin.get_queryset()
        # Evita .model.objects.all() (que omite el SaaSMixin) y el filtro manual
        # dependiente de self.request.agencia (no siempre seteado por el middleware).
        base_qs = self.get_queryset()
        context["total_facturas"] = base_qs.count()
        context["facturas_pendientes"] = base_qs.filter(estado="BORRADOR").count()
        return context


class FacturaDetailView(HtmxResponseMixin, SaaSMixin, LoginRequiredMixin, DetailView):
    model = Factura
    template_name = "core/erp/facturacion/detalle.html"
    htmx_template_name = "finance/partials/factura_detalle_htmx.html"
    context_object_name = "factura"
    # 🔐 SaaSMixin.get_queryset() filtra por agencia — Django usa ese QS en DetailView

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["items"] = self.object.items.all()
        return context


@agency_role_required(
    ["admin", "gerente", "contador"]
)  # Contador también puede facturar según rol clásico
def generar_factura_desde_venta(request, pk):
    """
    Vista para generar una factura desde una venta.
    🔐 CANDADO: Verifica que la venta pertenezca a la agencia del usuario.
    """
    agencia = get_agencia_or_403(request)
    venta = get_object_tenant_or_404(Venta, agencia, pk=pk)

    if venta.factura:
        messages.warning(
            request, f"La venta {venta.localizador or venta.pk} ya tiene una factura asociada."
        )
        return redirect("bookings:venta_detail", pk=pk)

    if not venta.cliente:
        messages.error(request, _("La venta debe tener un cliente asignado para poder facturar."))
        return redirect("bookings:venta_detail", pk=pk)

    try:
        factura = FacturacionService.generar_factura_desde_venta(venta, venta.cliente)

        if request.headers.get("HX-Request"):
            # Return partial for the modal
            from django.shortcuts import render

            return render(
                request, "finance/partials/invoice_detail_modal.html", {"invoice": factura}
            )

        messages.success(request, f"Factura {factura.numero_control} generada exitosamente.")
        return redirect("core:factura_detalle", pk=factura.pk)
    except Exception:
        logger.exception("Error generando factura desde venta %s", pk)
        error_msg = "Error al generar la factura. Contacte a soporte."
        if request.headers.get("HX-Request"):
            return HttpResponse(
                f'<div class="p-4 bg-red-900/20 text-red-400 rounded-xl border border-red-900/50">{error_msg}</div>',
                status=500,
            )
        messages.error(request, error_msg)
        return redirect("bookings:venta_detail", pk=pk)


def descargar_pdf_factura(request, pk):
    agencia = get_agencia_or_403(request)
    factura = get_object_tenant_or_404(Factura, agencia, pk=pk)
    try:
        from apps.finance.services.factura_pdf_generator import guardar_pdf_factura

        pdf_content = guardar_pdf_factura(factura)
        if pdf_content:
            response = HttpResponse(pdf_content, content_type="application/pdf")
            response["Content-Disposition"] = (
                f'attachment; filename="factura-{factura.numero_control}.pdf"'
            )
            return response
    except Exception:
        logger.exception("Error al generar PDF de factura %s", pk)
    messages.error(request, _("El PDF de esta factura no está disponible."))
    return redirect("core:factura_detalle", pk=pk)


@agency_role_required(
    ["admin", "gerente"]
)  # Ojo: Solo roles gerenciales pueden emitir definidamente
def emitir_factura_definitiva(request, pk):
    """
    Cambia el estado de una factura de BORRADOR a EMITIDA.
    🔐 CANDADO: Verifica que la factura pertenezca a la agencia del usuario.
    """
    agencia = get_agencia_or_403(request)
    factura = get_object_tenant_or_404(Factura, agencia, pk=pk)

    if factura.estado != Factura.EstadoFactura.BORRADOR:
        messages.warning(request, f"La factura {factura.numero_control} ya no está en borrador.")
        return redirect("core:factura_detalle", pk=pk)

    try:
        factura.estado = Factura.EstadoFactura.EMITIDA
        factura.save()

        messages.success(request, f"Factura {factura.numero_control} emitida correctamente.")
        return redirect("core:factura_detalle", pk=pk)
    except Exception as e:
        logger.exception("Error emitiendo factura %s", pk)
        messages.error(request, f"Error al emitir factura: {e}")
        return redirect("core:factura_detalle", pk=pk)

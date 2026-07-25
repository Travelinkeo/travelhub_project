"""Vistas (views) de la aplicación bookings.
"""

import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from apps.bookings.forms import FeeVentaForm
from apps.bookings.models import BoletoImportado, FeeVenta, Venta
from apps.crm.models import Cliente
from core.api import (
    HtmxResponseMixin,
    SaaSMixin,
    get_agencia_or_403,
    get_object_tenant_or_404,
    get_user_active_agency,
)

logger = logging.getLogger(__name__)


class VentaUpdateView:
    """Vista para gestionar ventaupdate. Uso: instanciar según necesidad del dominio.
    """
    model = Venta
    template_name = "core/venta_edit_glass_v2.html"
    fields = ["cliente", "localizador", "estado"]
    fields = ["cliente", "localizador", "estado"]
    # success_url = reverse_lazy('core:modern_dashboard') # Overridden by get_success_url

    def get_success_url(self):
        # Support for 'next' parameter to return to Admin or specific page
        next_url = self.request.GET.get("next") or self.request.POST.get("next")
        if next_url:
            from django.utils.http import url_has_allowed_host_and_scheme

            if url_has_allowed_host_and_scheme(url=next_url, allowed_hosts=None):
                return next_url
        return reverse_lazy("core:modern_dashboard")

    def get_context_data(self, **kwargs):
        # get_context_data: Obtiene/recupera context data. Args: según implementación. Returns: dato solicitado.
        context = super().get_context_data(**kwargs)
        # Pass 'next' to template to preserve it in POST
        context["next"] = self.request.GET.get("next")
        # Pasar el primer item para pre-llenar los inputs manuales (con select_related)
        context["first_item"] = self.object.items_venta.select_related(
            "producto_servicio", "moneda"
        ).first()
        return context

    def form_valid(self, form):
        # form_valid: Form valid. Args: según implementación. Returns: según implementación.
        response = super().form_valid(form)

        # Actualizar datos del Item (Financieros) - usar select_related
        item = self.object.items_venta.select_related("producto_servicio", "moneda").first()
        if item:
            try:
                precio = self.request.POST.get("item_precio")
                costo = self.request.POST.get("item_costo")
                comision = self.request.POST.get("item_comision")

                if precio:
                    item.precio_unitario_venta = precio
                if costo:
                    item.costo_neto_proveedor = costo
                if comision:
                    item.comision_agencia_monto = comision

                # Recalcular totales del item
                item.impuestos_item_venta = 0  # Simplificación por ahora
                item.save()

                # Recalcular Venta desde Servicio
                from apps.bookings.services.venta_service import VentaService

                VentaService.recalculate_finances(self.object.pk)

            except Exception:
                logger.exception("Error actualizando item financiero de venta %s", self.object.pk)
                messages.warning(
                    self.request,
                    "La venta se guardó, pero no se pudieron recalcular los importes del ítem. "
                    "Revise la pestaña de finanzas.",
                )

        return response


class VentasDashboardView:
    """Vista para gestionar ventasdashboard. Uso: instanciar según necesidad del dominio.
    """
    model = Venta
    template_name = "core/erp/ventas/dashboard.html"
    htmx_template_name = "bookings/partials/venta_list_htmx.html"
    context_object_name = "ventas"
    paginate_by = 20

    def get_queryset(self):
        # SaaSMixin filters by agency first
        queryset = super().get_queryset()
        queryset = (
            queryset.select_related("cliente", "moneda", "agencia", "creado_por")
            .prefetch_related(
                "boletos_adjuntos", "items_venta__producto_servicio", "pagos_venta__moneda"
            )
            .order_by("-fecha_venta")
        )

        # Search
        q = self.request.GET.get("q")
        if q:
            queryset = queryset.filter(
                Q(localizador__icontains=q)
                | Q(cliente__nombres__icontains=q)
                | Q(cliente__apellidos__icontains=q)
                | Q(id_venta__icontains=q)
            )

        # Filters
        estado = self.request.GET.get("estado")
        if estado:
            queryset = queryset.filter(estado=estado)

        return queryset

    def get_context_data(self, **kwargs):
        # get_context_data: Obtiene/recupera context data. Args: según implementación. Returns: dato solicitado.
        context = super().get_context_data(**kwargs)
        context["active_tab"] = "ventas"

        # Stats for the dashboard header (Filtered by Agency)
        # We reconstruct the base queryset for the agency to avoid applying search filters to stats
        base_qs = Venta.objects.select_related("cliente", "moneda", "agencia")
        agencia = get_user_active_agency(self.request.user)
        if agencia:
            base_qs = base_qs.filter(agencia=agencia)

        context["total_ventas_mes"] = base_qs.count()  # Simplified for POC
        context["monto_total_mes"] = base_qs.aggregate(Sum("total_venta"))["total_venta__sum"] or 0
        context["pendientes_pago"] = base_qs.filter(estado="PEN").count()

        return context


class VentaCreateView:
    """Vista para gestionar ventacreate. Uso: instanciar según necesidad del dominio.
    """
    model = Venta
    template_name = "core/erp/ventas/form.html"
    fields = ["cliente", "moneda", "estado"]
    success_url = reverse_lazy("core:ventas_dashboard")

    def get_context_data(self, **kwargs):
        # get_context_data: Obtiene/recupera context data. Args: según implementación. Returns: dato solicitado.
        context = super().get_context_data(**kwargs)
        context["active_tab"] = "ventas"
        context["title"] = "Nueva Venta"
        return context


class VentaDetailView:
    """Vista para gestionar ventadetail. Uso: instanciar según necesidad del dominio.
    """
    model = Venta
    template_name = "core/erp/ventas/detalle_final.html"
    # Esta es la magia reactiva: si HTMX pide la vista, devolvemos solo este fragmento
    htmx_template_name = "ventas/partials/detalle_htmx.html"
    context_object_name = "venta"

    def get_context_data(self, **kwargs):
        # get_context_data: Obtiene/recupera context data. Args: según implementación. Returns: dato solicitado.
        context = super().get_context_data(**kwargs)
        context["active_tab"] = "ventas"

        # Related objects - Optimized with select_related and prefetch_related
        context["boletos"] = BoletoImportado.objects.filter(
            venta_asociada=self.object
        ).select_related("proveedor", "agencia", "moneda")

        context["items"] = self.object.items_venta.select_related(
            "producto_servicio", "moneda"
        ).all()

        context["pagos"] = self.object.pagos_venta.select_related("moneda").all()

        # 🧠 Sales Intelligence AI
        from django.utils.module_loading import import_string

        ai_tips = []

        try:
            AIParserService = import_string(
                "apps.automation.services.ai_parser_service.AIParserService"
            )
            # Analizar boletos para obtener tips reales
            for boleto in context["boletos"]:
                # Simular data para el analizador (luego esto vendrá de un JSON field)
                mock_data = {
                    "boletos": [
                        {"itinerario": [{"origen": boleto.origen, "destino": boleto.destino}]}
                    ]
                }
                ai_tips.extend(AIParserService.analyze_sales_opportunities(mock_data))
        except Exception as e:
            logger.warning("Error generando tips IA para venta %s: %s", self.object.pk, e)

        context["ai_tips"] = list(set(ai_tips))[:3]  # Max 3 tips únicos

        return context


class VentaAssignClientView:
    """Vista para gestionar ventaassignclient. Uso: instanciar según necesidad del dominio.
    """
    def post(self, request, pk):
        # 🔐 CANDADO: Solo accede a ventas de la agencia del usuario.
        agencia = get_agencia_or_403(request)
        venta = get_object_tenant_or_404(Venta, agencia, pk=pk)
        cliente_id = request.POST.get("cliente_id")

        if cliente_id:
            cliente = get_object_or_404(Cliente, pk=cliente_id)
            venta.cliente = cliente
            venta.save()
            messages.success(request, f"Cliente {cliente} asignado correctamente.")
        else:
            messages.error(request, _("Debe seleccionar un cliente."))

        return redirect("bookings:venta_detail", pk=pk)


class VentaAddFeeView:
    """Vista para gestionar ventaaddfee. Uso: instanciar según necesidad del dominio.
    """
    model = FeeVenta
    form_class = FeeVentaForm
    template_name = "core/erp/ventas/fee_form.html"

    def dispatch(self, request, *args, **kwargs):
        # 🔐 CANDADO: Solo accede a ventas de la agencia del usuario.
        agencia = get_agencia_or_403(request)
        self.venta = get_object_tenant_or_404(Venta, agencia, pk=self.kwargs["pk"])
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        # form_valid: Form valid. Args: según implementación. Returns: según implementación.
        fee = form.save(commit=False)
        fee.venta = self.venta
        fee.save()
        # self.venta.recalcular_finanzas()
        from apps.bookings.services.venta_service import VentaService

        VentaService.recalculate_finances(self.venta.pk)
        messages.success(self.request, "Fee registrado exitosamente.")
        return redirect("bookings:venta_detail", pk=self.venta.pk)

    def get_context_data(self, **kwargs):
        # get_context_data: Obtiene/recupera context data. Args: según implementación. Returns: dato solicitado.
        context = super().get_context_data(**kwargs)
        context["venta"] = self.venta
        return context


@login_required
def eliminar_venta(request, pk):
    """🗑️ Eliminación física de una venta y sus ítems."""
    agencia = get_agencia_or_403(request)
    # Buscamos con all_objects por si estuviera soft-deleted
    venta = get_object_tenant_or_404(Venta.all_objects, agencia, pk=pk)

    try:
        # Borrar físicamente (HARD DELETE)
        # Esto borrará también items, segmentos, pagos, etc (por CASCADE en DB)
        venta.hard_delete()
        messages.success(request, f"Venta {pk} eliminada físicamente con éxito.")
    except Exception as e:
        logger.exception("Error en hard_delete de venta %s", pk)
        messages.error(request, f"Error al eliminar venta: {str(e)}")

    next_url = request.GET.get("next")
    from django.utils.http import url_has_allowed_host_and_scheme

    if next_url and url_has_allowed_host_and_scheme(url=next_url, allowed_hosts=None):
        return redirect(next_url)
    return redirect("core:modern_dashboard")

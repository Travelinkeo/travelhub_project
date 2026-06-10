# apps/finance/views/admin_views.py
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from apps.finance.models import RetencionISLR
from apps.finance.models.currencies import Moneda, TipoCambio
from core.api import SaaSMixin

# --- Vistas para Moneda ---


class MonedaListView(SaaSMixin, LoginRequiredMixin, ListView):
    model = Moneda
    template_name = "finance/admin/monedas_y_tasas.html"
    context_object_name = "monedas"

    def get_queryset(self):
        return Moneda.objects.all().order_by("nombre")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["tasas"] = TipoCambio.objects.select_related(
            "moneda_origen", "moneda_destino"
        ).order_by("-fecha_efectiva")[:10]
        return context


class MonedaCreateView(SaaSMixin, LoginRequiredMixin, CreateView):
    model = Moneda
    template_name = "finance/admin/moneda_form.html"
    fields = ["nombre", "codigo_iso", "simbolo", "es_moneda_local"]
    success_url = reverse_lazy("finance_admin:moneda_list")

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        for field in form.fields.values():
            field.widget.attrs["class"] = "input-base"
        return form

    def form_valid(self, form):
        messages.success(self.request, "Moneda creada exitosamente.")
        return super().form_valid(form)


class MonedaUpdateView(SaaSMixin, LoginRequiredMixin, UpdateView):
    model = Moneda
    template_name = "finance/admin/moneda_form.html"
    fields = ["nombre", "codigo_iso", "simbolo", "es_moneda_local"]
    success_url = reverse_lazy("finance_admin:moneda_list")

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        for field in form.fields.values():
            field.widget.attrs["class"] = "input-base"
        return form

    def form_valid(self, form):
        messages.success(self.request, "Moneda actualizada exitosamente.")
        return super().form_valid(form)


class MonedaDeleteView(SaaSMixin, LoginRequiredMixin, DeleteView):
    model = Moneda
    template_name = "core/erp/catalogos/confirm_delete_generic.html"
    success_url = reverse_lazy("finance_admin:moneda_list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["object_name"] = "Moneda"
        context["object_instance"] = f"{self.object.nombre} ({self.object.codigo_iso})"
        context["cancel_url"] = self.success_url
        return context

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Moneda eliminada correctamente.")
        return super().delete(request, *args, **kwargs)


# --- Vistas para TipoCambio ---


class TipoCambioCreateView(SaaSMixin, LoginRequiredMixin, CreateView):
    model = TipoCambio
    template_name = "finance/admin/tipocambio_form.html"
    fields = ["moneda_origen", "moneda_destino", "fecha_efectiva", "tasa_conversion"]
    success_url = reverse_lazy("finance_admin:moneda_list")

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        for field in form.fields.values():
            field.widget.attrs["class"] = "input-base"
        return form

    def form_valid(self, form):
        messages.success(self.request, "Tasa de Cambio creada exitosamente.")
        return super().form_valid(form)


class TipoCambioUpdateView(SaaSMixin, LoginRequiredMixin, UpdateView):
    model = TipoCambio
    template_name = "finance/admin/tipocambio_form.html"
    fields = ["moneda_origen", "moneda_destino", "fecha_efectiva", "tasa_conversion"]
    success_url = reverse_lazy("finance_admin:moneda_list")

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        for field in form.fields.values():
            field.widget.attrs["class"] = "input-base"
        return form

    def form_valid(self, form):
        messages.success(self.request, "Tasa de Cambio actualizada exitosamente.")
        return super().form_valid(form)


class TipoCambioDeleteView(SaaSMixin, LoginRequiredMixin, DeleteView):
    model = TipoCambio
    template_name = "core/erp/catalogos/confirm_delete_generic.html"
    success_url = reverse_lazy("finance_admin:moneda_list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["object_name"] = "Tasa de Cambio"
        context["object_instance"] = f"{self.object}"
        context["cancel_url"] = self.success_url
        return context

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Tasa de Cambio eliminada correctamente.")
        return super().delete(request, *args, **kwargs)


# --- Vistas para RetencionISLR ---


class RetencionISLRListView(SaaSMixin, LoginRequiredMixin, ListView):
    model = RetencionISLR
    template_name = "finance/admin/retencionislr_list.html"
    context_object_name = "retenciones"
    paginate_by = 30

    def get_queryset(self):
        q = self.request.GET.get("q")
        queryset = RetencionISLR.objects.select_related("factura", "cliente").order_by(
            "-fecha_emision"
        )
        if q:
            queryset = queryset.filter(
                Q(numero_comprobante__icontains=q)
                | Q(cliente__nombre_completo__icontains=q)
                | Q(factura__numero_factura__icontains=q)
            )
        return queryset


class RetencionISLRCreateView(SaaSMixin, LoginRequiredMixin, CreateView):
    model = RetencionISLR
    template_name = "finance/admin/retencionislr_form.html"
    fields = [
        "factura",
        "cliente",
        "numero_comprobante",
        "fecha_emision",
        "monto_base",
        "porcentaje_retencion",
        "monto_retenido",
        "estado",
        "periodo_fiscal",
    ]
    success_url = reverse_lazy("finance_admin:retencionislr_list")

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        for field in form.fields.values():
            field.widget.attrs["class"] = "input-base"
        return form

    def form_valid(self, form):
        messages.success(self.request, "Retención ISLR creada exitosamente.")
        return super().form_valid(form)


class RetencionISLRUpdateView(SaaSMixin, LoginRequiredMixin, UpdateView):
    model = RetencionISLR
    template_name = "finance/admin/retencionislr_form.html"
    fields = [
        "factura",
        "cliente",
        "numero_comprobante",
        "fecha_emision",
        "monto_base",
        "porcentaje_retencion",
        "monto_retenido",
        "estado",
        "periodo_fiscal",
    ]
    success_url = reverse_lazy("finance_admin:retencionislr_list")

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        for field in form.fields.values():
            field.widget.attrs["class"] = "input-base"
        return form

    def form_valid(self, form):
        messages.success(self.request, "Retención ISLR actualizada exitosamente.")
        return super().form_valid(form)


class RetencionISLRDeleteView(SaaSMixin, LoginRequiredMixin, DeleteView):
    model = RetencionISLR
    template_name = "core/erp/catalogos/confirm_delete_generic.html"
    success_url = reverse_lazy("finance_admin:retencionislr_list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["object_name"] = "Retención ISLR"
        context["object_instance"] = self.object.numero_comprobante
        context["cancel_url"] = self.success_url
        return context

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Retención ISLR eliminada correctamente.")
        return super().delete(request, *args, **kwargs)

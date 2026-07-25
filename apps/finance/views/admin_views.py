# apps/finance/views/admin_views.py
"""Vistas (views) de la aplicación finance.
"""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from apps.common.models import Moneda
from core.api import SaaSMixin


class MonedaListView:
    """Vista para gestionar monedalist. Uso: instanciar según necesidad del dominio.
    """
    model = Moneda
    template_name = "finance/admin/monedas_y_tasas.html"
    context_object_name = "monedas"

    def get_queryset(self):
        # get_queryset: Obtiene/recupera queryset. Args: según implementación. Returns: dato solicitado.
        return Moneda.objects.all().order_by("nombre")

    def get_context_data(self, **kwargs):
        # get_context_data: Obtiene/recupera context data. Args: según implementación. Returns: dato solicitado.
        context = super().get_context_data(**kwargs)
        context["tasas"] = []
        return context


class MonedaCreateView:
    """Vista para gestionar monedacreate. Uso: instanciar según necesidad del dominio.
    """
    model = Moneda
    template_name = "finance/admin/moneda_form.html"
    fields = ["nombre", "codigo_iso", "simbolo", "es_moneda_local"]
    success_url = reverse_lazy("finance_admin:moneda_list")

    def get_form(self, form_class=None):
        # get_form: Obtiene/recupera form. Args: según implementación. Returns: dato solicitado.
        form = super().get_form(form_class)
        for field in form.fields.values():
            field.widget.attrs["class"] = "input-base"
        return form

    def form_valid(self, form):
        # form_valid: Form valid. Args: según implementación. Returns: según implementación.
        messages.success(self.request, "Moneda creada exitosamente.")
        return super().form_valid(form)


class MonedaUpdateView:
    """Vista para gestionar monedaupdate. Uso: instanciar según necesidad del dominio.
    """
    model = Moneda
    template_name = "finance/admin/moneda_form.html"
    fields = ["nombre", "codigo_iso", "simbolo", "es_moneda_local"]
    success_url = reverse_lazy("finance_admin:moneda_list")

    def get_form(self, form_class=None):
        # get_form: Obtiene/recupera form. Args: según implementación. Returns: dato solicitado.
        form = super().get_form(form_class)
        for field in form.fields.values():
            field.widget.attrs["class"] = "input-base"
        return form

    def form_valid(self, form):
        # form_valid: Form valid. Args: según implementación. Returns: según implementación.
        messages.success(self.request, "Moneda actualizada exitosamente.")
        return super().form_valid(form)


class MonedaDeleteView:
    """Vista para gestionar monedadelete. Uso: instanciar según necesidad del dominio.
    """
    model = Moneda
    template_name = "core/erp/catalogos/confirm_delete_generic.html"
    success_url = reverse_lazy("finance_admin:moneda_list")

    def get_context_data(self, **kwargs):
        # get_context_data: Obtiene/recupera context data. Args: según implementación. Returns: dato solicitado.
        context = super().get_context_data(**kwargs)
        context["object_name"] = "Moneda"
        context["object_instance"] = f"{self.object.nombre} ({self.object.codigo_iso})"
        context["cancel_url"] = self.success_url
        return context

    def delete(self, request, *args, **kwargs):
        # delete: Elimina el objeto de la base de datos. Args: None. Returns: None.
        messages.success(self.request, "Moneda eliminada correctamente.")
        return super().delete(request, *args, **kwargs)

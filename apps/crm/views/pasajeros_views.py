from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from apps.crm.forms import PasajeroForm
from apps.crm.models import Pasajero
from core.api import HtmxResponseMixin, SaaSMixin


class CRMBaseMixin(SaaSMixin, LoginRequiredMixin):
    context_object_name = "object"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["active_tab"] = "crm"
        return context


class PasajeroListView(HtmxResponseMixin, CRMBaseMixin, ListView):
    model = Pasajero
    template_name = "crm/pasajero_list.html"
    htmx_template_name = "crm/partials/pasajero_list_rows.html"
    context_object_name = "pasajeros"
    paginate_by = 25

    def get_queryset(self):
        queryset = (
            super()
            .get_queryset()
            .prefetch_related("clientes_asociados")
            .order_by("apellidos", "nombres")
        )
        q = self.request.GET.get("q")
        if q:
            queryset = queryset.filter(
                Q(nombres__icontains=q)
                | Q(apellidos__icontains=q)
                | Q(numero_pasaporte__icontains=q)
                | Q(cedula_identidad__icontains=q)
                | Q(numero_documento__icontains=q)  # Added from core version
            )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Pasajeros"
        return context


class PasajeroDetailView(CRMBaseMixin, DetailView):
    model = Pasajero
    template_name = "crm/pasajero_detail.html"
    context_object_name = "pasajero"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = f"Pasajero: {self.object.get_full_name()}"
        return context


class PasajeroCreateView(CRMBaseMixin, CreateView):
    model = Pasajero
    template_name = "crm/pasajero_form.html"
    form_class = PasajeroForm
    success_url = reverse_lazy("crm:pasajero_list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Nuevo Pasajero"
        return context

    def form_valid(self, form):
        messages.success(self.request, "Pasajero creado exitosamente.")
        return super().form_valid(form)


class PasajeroUpdateView(CRMBaseMixin, UpdateView):
    model = Pasajero
    template_name = "crm/pasajero_form.html"
    form_class = PasajeroForm

    def get_success_url(self):
        return reverse_lazy("crm:pasajero_detail", kwargs={"pk": self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Editar Pasajero"
        return context

    def form_valid(self, form):
        messages.success(self.request, "Pasajero actualizado exitosamente.")
        return super().form_valid(form)


class PasajeroDeleteView(CRMBaseMixin, DeleteView):
    model = Pasajero
    template_name = "crm/pasajero_confirm_delete.html"
    success_url = reverse_lazy("crm:pasajero_list")

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Pasajero eliminado correctamente.")
        return super().delete(request, *args, **kwargs)

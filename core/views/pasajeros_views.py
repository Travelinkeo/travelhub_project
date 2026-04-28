from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.contrib import messages
from django.db.models import Q

from apps.crm.models import Pasajero
from core.forms import PasajeroForm
from core.mixins import SaaSMixin

class PasajeroListView(SaaSMixin, LoginRequiredMixin, ListView):
    model = Pasajero
    template_name = 'core/erp/pasajeros/list.html'
    context_object_name = 'pasajeros'
    paginate_by = 20

    def get_queryset(self):
        queryset = super().get_queryset()
        q = self.request.GET.get('q')
        if q:
            queryset = queryset.filter(
                Q(nombres__icontains=q) | 
                Q(apellidos__icontains=q) |
                Q(numero_documento__icontains=q) |
                Q(email__icontains=q)
            )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Pasajeros'
        context['active_tab'] = 'pasajeros'
        return context

class PasajeroCreateView(SaaSMixin, LoginRequiredMixin, CreateView):
    model = Pasajero
    form_class = PasajeroForm
    template_name = 'core/erp/pasajeros/form.html'
    success_url = reverse_lazy('core:pasajeros_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Nuevo Pasajero'
        context['active_tab'] = 'pasajeros'
        return context

    def form_valid(self, form):
        messages.success(self.request, "Pasajero creado exitosamente.")
        return super().form_valid(form)

class PasajeroUpdateView(SaaSMixin, LoginRequiredMixin, UpdateView):
    model = Pasajero
    form_class = PasajeroForm
    template_name = 'core/erp/pasajeros/form.html'
    success_url = reverse_lazy('core:pasajeros_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Editar Pasajero'
        context['active_tab'] = 'pasajeros'
        return context

    def form_valid(self, form):
        messages.success(self.request, "Pasajero actualizado exitosamente.")
        return super().form_valid(form)

class PasajeroDeleteView(SaaSMixin, LoginRequiredMixin, DeleteView):
    model = Pasajero
    template_name = 'core/erp/pasajeros/delete.html'
    success_url = reverse_lazy('core:pasajeros_list')

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Pasajero eliminado.")
        return super().delete(request, *args, **kwargs)

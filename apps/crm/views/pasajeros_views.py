from django.contrib import messages
from django.db.models import Q
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin

from apps.crm.models import Pasajero
from core.forms.legacy import PasajeroForm
from core.mixins import SaaSMixin

class CRMBaseMixin(SaaSMixin, LoginRequiredMixin):
    context_object_name = 'object'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_tab'] = 'crm'
        return context

class PasajeroListView(CRMBaseMixin, ListView):
    model = Pasajero
    template_name = 'crm/pasajero_list.html'
    context_object_name = 'pasajeros'
    paginate_by = 25

    def get_queryset(self):
        queryset = super().get_queryset().order_by('apellidos', 'nombres')
        q = self.request.GET.get('q')
        if q:
            queryset = queryset.filter(
                Q(nombres__icontains=q) |
                Q(apellidos__icontains=q) |
                Q(numero_pasaporte__icontains=q) |
                Q(cedula_identidad__icontains=q)
            )
        return queryset

class PasajeroDetailView(CRMBaseMixin, DetailView):
    model = Pasajero
    template_name = 'crm/pasajero_detail.html'
    context_object_name = 'pasajero'

class PasajeroCreateView(CRMBaseMixin, CreateView):
    model = Pasajero
    template_name = 'crm/pasajero_form.html'
    form_class = PasajeroForm
    success_url = reverse_lazy('crm:pasajero_list')

class PasajeroUpdateView(CRMBaseMixin, UpdateView):
    model = Pasajero
    template_name = 'crm/pasajero_form.html'
    form_class = PasajeroForm
    
    def get_success_url(self):
        return reverse_lazy('crm:pasajero_detail', kwargs={'pk': self.object.pk})

class PasajeroDeleteView(CRMBaseMixin, DeleteView):
    model = Pasajero
    template_name = 'crm/pasajero_confirm_delete.html'
    success_url = reverse_lazy('crm:pasajero_list')

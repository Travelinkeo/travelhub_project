from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin

from apps.crm.models import Cliente
from core.mixins import SaaSMixin, HtmxResponseMixin

class CRMBaseMixin(SaaSMixin, LoginRequiredMixin):
    context_object_name = 'object'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_tab'] = 'crm'
        return context

class ClienteListView(HtmxResponseMixin, CRMBaseMixin, ListView):
    model = Cliente
    template_name = 'crm/cliente_list.html' # Preferring app template
    htmx_template_name = 'crm/partials/cliente_list_table.html'
    context_object_name = 'clientes'
    paginate_by = 25

    def get_queryset(self):
        queryset = super().get_queryset().select_related('ciudad', 'nacionalidad').order_by('apellidos', 'nombres')
        q = self.request.GET.get('q')
        tipo = self.request.GET.get('tipo')
        if q:
            queryset = queryset.filter(
                Q(nombres__icontains=q) |
                Q(apellidos__icontains=q) |
                Q(cedula_identidad__icontains=q) |
                Q(nombre_empresa__icontains=q) |
                Q(email__icontains=q)
            )
        if tipo:
            queryset = queryset.filter(tipo_cliente=tipo)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from django.utils import timezone
        hoy = timezone.now()
        base_qs = self.get_queryset()
        context['clientes_corp_count'] = base_qs.filter(tipo_cliente='COR').count()
        context['clientes_vip_count'] = base_qs.filter(tipo_cliente='VIP').count()
        context['clientes_nuevos_mes'] = base_qs.filter(
            fecha_registro__year=hoy.year,
            fecha_registro__month=hoy.month
        ).count()
        context['tipos_cliente'] = Cliente.TipoCliente.choices
        return context

class ClienteDetailView(CRMBaseMixin, DetailView):
    model = Cliente
    template_name = 'crm/cliente_detail.html'
    context_object_name = 'cliente'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from apps.cotizaciones.models import Cotizacion
        context['cotizaciones'] = Cotizacion.objects.filter(cliente=self.object).select_related('moneda', 'consultor').order_by('-fecha_emision')
        return context

class ClienteCreateView(CRMBaseMixin, CreateView):
    model = Cliente
    template_name = 'crm/cliente_form.html'
    fields = [
        'foto_perfil', 'tipo_cliente', 'nombres', 'apellidos', 
        'nombre_empresa', 'cedula_identidad', 'email', 'telefono_principal',
        'nacionalidad', 'direccion', 'ciudad'
    ]
    success_url = reverse_lazy('crm:cliente_list')

    def form_valid(self, form):
        messages.success(self.request, "Cliente creado correctamente.")
        return super().form_valid(form)

class ClienteUpdateView(CRMBaseMixin, UpdateView):
    model = Cliente
    template_name = 'crm/cliente_form.html'
    fields = [
        'foto_perfil', 'tipo_cliente', 'nombres', 'apellidos', 
        'nombre_empresa', 'cedula_identidad', 'email', 'telefono_principal',
        'nacionalidad', 'direccion', 'ciudad'
    ]
    
    def get_success_url(self):
        return reverse_lazy('crm:cliente_detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        messages.success(self.request, "Cliente actualizado correctamente.")
        return super().form_valid(form)

class ClienteDeleteView(CRMBaseMixin, DeleteView):
    model = Cliente
    success_url = reverse_lazy('crm:cliente_list')
    template_name = 'crm/cliente_confirm_delete.html'

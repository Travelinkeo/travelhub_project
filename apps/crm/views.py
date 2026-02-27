from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.db.models import Q
from django.contrib import messages
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, JsonResponse
from .models import Cliente, Pasajero
from core.mixins import SaaSMixin
from cotizaciones.models import Cotizacion

class CRMBaseMixin(SaaSMixin, LoginRequiredMixin):
    context_object_name = 'object'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_tab'] = 'crm'
        return context

# --- CLIENTES ---

class ClienteListView(CRMBaseMixin, ListView):
    model = Cliente
    template_name = 'crm/cliente_list.html'
    context_object_name = 'clientes'
    paginate_by = 25

    def get_queryset(self):
        queryset = super().get_queryset().order_by('apellidos', 'nombres')
        q = self.request.GET.get('q')
        if q:
            queryset = queryset.filter(
                Q(nombres__icontains=q) |
                Q(apellidos__icontains=q) |
                Q(cedula_identidad__icontains=q) |
                Q(nombre_empresa__icontains=q) |
                Q(email__icontains=q)
            )
        return queryset

    def get_template_names(self):
        if self.request.headers.get('HX-Request'):
            return ['crm/partials/cliente_list_table.html']
        return [self.template_name]

class ClienteDetailView(CRMBaseMixin, DetailView):
    model = Cliente
    template_name = 'crm/cliente_detail.html'
    context_object_name = 'cliente'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['cotizaciones'] = Cotizacion.objects.filter(cliente=self.object).order_by('-fecha_emision')
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

# --- PASAJEROS ---

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
                Q(numero_documento__icontains=q)
            )
        return queryset

class PasajeroDetailView(CRMBaseMixin, DetailView):
    model = Pasajero
    template_name = 'crm/pasajero_detail.html'
    context_object_name = 'pasajero'

class PasajeroCreateView(CRMBaseMixin, CreateView):
    model = Pasajero
    template_name = 'crm/pasajero_form.html'
    fields = [
        'nombres', 'apellidos', 'fecha_nacimiento', 'tipo_documento', 
        'numero_documento', 'nacionalidad', 'pais_emision_documento',
        'fecha_vencimiento_documento', 'email', 'telefono'
    ]
    success_url = reverse_lazy('crm:pasajero_list')

class PasajeroUpdateView(CRMBaseMixin, UpdateView):
    model = Pasajero
    template_name = 'crm/pasajero_form.html'
    fields = [
        'nombres', 'apellidos', 'fecha_nacimiento', 'tipo_documento', 
        'numero_documento', 'nacionalidad', 'pais_emision_documento',
        'fecha_vencimiento_documento', 'email', 'telefono'
    ]
    
    def get_success_url(self):
        return reverse_lazy('crm:pasajero_detail', kwargs={'pk': self.object.pk})

# --- ACCIONES CRM ---

class PasajeroSearchView(CRMBaseMixin, View):
    def get(self, request, *args, **kwargs):
        q = request.GET.get('q', '').strip()
        if len(q) < 2:
            return HttpResponse('<p class="text-gray-500 text-sm text-center py-4">Sigue escribiendo...</p>')
            
        pasajeros = Pasajero.objects.filter(
            Q(nombres__icontains=q) | 
            Q(apellidos__icontains=q) | 
            Q(numero_documento__icontains=q)
        ).exclude(clientes=request.GET.get('cliente_id'))[:10]
        
        return render(request, 'crm/partials/pasajero_search_results.html', {
            'pasajeros': pasajeros,
            'cliente_id': request.GET.get('cliente_id')
        })

class VincularPasajeroActionView(CRMBaseMixin, View):
    def post(self, request, pk, *args, **kwargs):
        cliente = get_object_or_404(Cliente, pk=pk)
        pasajero_id = request.POST.get('pasajero_id')
        if pasajero_id:
            pasajero = get_object_or_404(Pasajero, pk=pasajero_id)
            cliente.pasajeros.add(pasajero)
            messages.success(request, f"Pasajero {pasajero.get_nombre_completo()} vinculado.")
        
        return HttpResponse(status=204, headers={'HX-Refresh': 'true'})

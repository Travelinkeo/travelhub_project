from django.views.generic import ListView, CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.db.models import Q
from django.contrib import messages
from apps.crm.models import Cliente
from core.mixins import SaaSMixin

class ClienteFormMixin:
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        for field_name, field in form.fields.items():
            if field_name == 'es_cliente_frecuente':
                field.widget.attrs['class'] = 'form-checkbox h-5 w-5 text-primary rounded border-gray-300 focus:ring-primary'
            else:
                field.widget.attrs['class'] = 'w-full bg-white border border-gray-300 rounded-lg px-4 py-2.5 text-gray-900 focus:ring-primary focus:border-primary'
        return form

class ClienteListView(SaaSMixin, LoginRequiredMixin, ListView):
    model = Cliente
    template_name = 'core/erp/clientes/list.html'
    context_object_name = 'clientes'
    paginate_by = 20

    def get_queryset(self):
        queryset = super().get_queryset().order_by('apellidos', 'nombres', 'nombre_empresa')
        
        q = self.request.GET.get('q')
        if q:
            queryset = queryset.filter(
                Q(nombres__icontains=q) |
                Q(apellidos__icontains=q) |
                Q(nombre_empresa__icontains=q) |
                Q(cedula_identidad__icontains=q) |
                Q(email__icontains=q)
            )
            
        tipo = self.request.GET.get('tipo')
        if tipo:
            queryset = queryset.filter(tipo_cliente=tipo)
            
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_tab'] = 'crm'
        context['tipos_cliente'] = Cliente.TipoCliente.choices
        return context

class ClienteCreateView(SaaSMixin, LoginRequiredMixin, ClienteFormMixin, CreateView):
    model = Cliente
    template_name = 'core/erp/clientes/form.html'
    fields = [
        'foto_perfil',
        'tipo_cliente', 'nombres', 'apellidos', 'nombre_empresa',
        'cedula_identidad', 'email', 'telefono_principal',
        'fecha_nacimiento', 'nacionalidad',
        'numero_pasaporte', 'pais_emision_pasaporte', 'fecha_expiracion_pasaporte',
        'direccion', 'ciudad', 'es_cliente_frecuente'
    ]
    success_url = reverse_lazy('core:clientes_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_tab'] = 'crm'
        context['title'] = 'Nuevo Cliente'
        return context

    def form_valid(self, form):
        messages.success(self.request, "Cliente creado exitosamente.")
        return super().form_valid(form)

class ClienteUpdateView(SaaSMixin, LoginRequiredMixin, ClienteFormMixin, UpdateView):
    model = Cliente
    template_name = 'core/erp/clientes/form.html'
    fields = [
        'foto_perfil',
        'tipo_cliente', 'nombres', 'apellidos', 'nombre_empresa',
        'cedula_identidad', 'email', 'telefono_principal',
        'fecha_nacimiento', 'nacionalidad',
        'numero_pasaporte', 'pais_emision_pasaporte', 'fecha_expiracion_pasaporte',
        'direccion', 'ciudad', 'es_cliente_frecuente'
    ]
    success_url = reverse_lazy('core:clientes_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_tab'] = 'crm'
        context['title'] = f'Editar Cliente: {self.object.get_nombre_completo()}'
        return context

    def form_valid(self, form):
        messages.success(self.request, "Cliente actualizado exitosamente.")
        return super().form_valid(form)

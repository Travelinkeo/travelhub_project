from django.views.generic import ListView, CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.db.models import Q
from django.contrib import messages
from core.models import Proveedor
from core.models_catalogos import Ciudad
from core.mixins import SaaSMixin

class ProveedorListView(SaaSMixin, LoginRequiredMixin, ListView):
    model = Proveedor
    template_name = 'core/erp/proveedores/list.html'
    context_object_name = 'proveedores'
    paginate_by = 20

    def get_queryset(self):
        queryset = super().get_queryset().order_by('nombre')
        
        q = self.request.GET.get('q')
        if q:
            queryset = queryset.filter(
                Q(nombre__icontains=q) |
                Q(alias__icontains=q) |
                Q(rif__icontains=q) |
                Q(contacto_nombre__icontains=q)
            )
            
        tipo = self.request.GET.get('tipo')
        if tipo:
            queryset = queryset.filter(tipo_proveedor=tipo)
            
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_tab'] = 'crm'
        context['tipos_proveedor'] = Proveedor.TipoProveedorChoices.choices
        return context

class ProveedorFormMixin:
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        for field_name, field in form.fields.items():
            if field_name == 'activo':
                field.widget.attrs['class'] = 'form-checkbox h-5 w-5 text-primary rounded border-gray-300 focus:ring-primary'
            else:
                field.widget.attrs['class'] = 'w-full bg-white border border-gray-300 rounded-lg px-4 py-2.5 text-gray-900 focus:ring-primary focus:border-primary'
        return form

class ProveedorCreateView(SaaSMixin, LoginRequiredMixin, ProveedorFormMixin, CreateView):
    model = Proveedor
    template_name = 'core/erp/proveedores/form.html'
    fields = [
        'nombre', 'alias', 'rif', 'tipo_proveedor', 'nivel_proveedor',
        'contacto_nombre', 'contacto_email', 'contacto_telefono',
        'direccion', 'ciudad', 'notas',
        'numero_cuenta_agencia', 'condiciones_pago', 'datos_bancarios',
        'fee_nacional', 'fee_internacional', 'activo',
        'iata', 'seudo_sabre', 'office_id_kiu', 'office_id_amadeus',
        'office_id_travelport', 'office_id_hotelbeds', 'office_id_expedia'
    ]
    success_url = reverse_lazy('core:proveedores_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_tab'] = 'crm'
        context['title'] = 'Nuevo Proveedor'
        return context

    def form_valid(self, form):
        messages.success(self.request, "Proveedor creado exitosamente.")
        return super().form_valid(form)

class ProveedorUpdateView(SaaSMixin, LoginRequiredMixin, ProveedorFormMixin, UpdateView):
    model = Proveedor
    template_name = 'core/erp/proveedores/form.html'
    fields = [
        'nombre', 'alias', 'rif', 'tipo_proveedor', 'nivel_proveedor',
        'contacto_nombre', 'contacto_email', 'contacto_telefono',
        'direccion', 'ciudad', 'notas',
        'numero_cuenta_agencia', 'condiciones_pago', 'datos_bancarios',
        'fee_nacional', 'fee_internacional', 'activo',
        'iata', 'seudo_sabre', 'office_id_kiu', 'office_id_amadeus',
        'office_id_travelport', 'office_id_hotelbeds', 'office_id_expedia'
    ]
    success_url = reverse_lazy('core:proveedores_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_tab'] = 'crm'
        context['title'] = f'Editar Proveedor: {self.object.nombre}'
        context['proveedor_id'] = self.object.pk
        # Serializar monedas disponibles para el frontend
        from core.models_catalogos import Moneda, ProductoServicio
        from core.serializers import MonedaSerializer
        context['monedas_json'] = MonedaSerializer(Moneda.objects.all(), many=True).data
        context['tipos_servicio_choices'] = [{'id': c[0], 'label': c[1]} for c in ProductoServicio.TipoProductoChoices.choices]
        return context

    def form_valid(self, form):
        messages.success(self.request, "Proveedor actualizado exitosamente.")
        return super().form_valid(form)

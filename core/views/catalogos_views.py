from django.shortcuts import redirect, render
from django.db.models import Q
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib import messages
from django.views import View

from core.models_catalogos import TipoCambio, Moneda, Aerolinea, Pais, Ciudad, ProductoServicio, Proveedor, ComisionProveedorServicio
from core.mixins import SaaSMixin
from apps.contabilidad.views_tasas import sincronizar_tasas_manual

class CatalogosCenterView(SaaSMixin, LoginRequiredMixin, ListView):
    model = Moneda # Dummy model to satisfy ListView
    template_name = 'core/erp/catalogos/center.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_tab'] = 'configuracion'
        return context

class AerolineaListView(SaaSMixin, LoginRequiredMixin, ListView):
    model = Aerolinea
    template_name = 'core/erp/catalogos/aerolineas_list.html'
    context_object_name = 'aerolineas'
    paginate_by = 30
    
    def get_queryset(self):
        q = self.request.GET.get('q')
        queryset = Aerolinea.objects.all().order_by('nombre')
        if q:
            queryset = queryset.filter(Q(nombre__icontains=q) | Q(codigo_iata__icontains=q))
        return queryset

class ProductoServicioListView(SaaSMixin, LoginRequiredMixin, ListView):
    model = ProductoServicio
    template_name = 'core/erp/catalogos/productos_list.html'
    context_object_name = 'productos'
    paginate_by = 30
    
    def get_queryset(self):
        q = self.request.GET.get('q')
        queryset = ProductoServicio.objects.all().order_by('nombre')
        if q:
            queryset = queryset.filter(Q(nombre__icontains=q) | Q(codigo_interno__icontains=q))
        return queryset

class PaisListView(SaaSMixin, LoginRequiredMixin, ListView):
    model = Pais
    template_name = 'core/erp/catalogos/geografia_list.html'
    context_object_name = 'paises'
    paginate_by = 30
    
    def get_queryset(self):
        q = self.request.GET.get('q')
        queryset = Pais.objects.all().order_by('nombre')
        if q:
            queryset = queryset.filter(Q(nombre__icontains=q) | Q(codigo_iso__icontains=q))
        return queryset

class GeografiaListView(SaaSMixin, LoginRequiredMixin, ListView):
    """Vista combinada para Geografía (Países y Ciudades)."""
    model = Ciudad
    template_name = 'core/erp/catalogos/geografia_list.html'
    context_object_name = 'ciudades'
    paginate_by = 30
    
    def get_queryset(self):
        q = self.request.GET.get('q')
        queryset = Ciudad.objects.select_related('pais').all().order_by('pais__nombre', 'nombre')
        if q:
            queryset = queryset.filter(Q(nombre__icontains=q) | Q(pais__nombre__icontains=q) | Q(codigo_iata__icontains=q))
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['paises_count'] = Pais.objects.count()
        return context

class TipoCambioListView(SaaSMixin, LoginRequiredMixin, ListView):
    model = TipoCambio
    template_name = 'core/config/tasas_list.html'
    context_object_name = 'tasas'
    paginate_by = 30

    def get_queryset(self):
        return TipoCambio.objects.select_related('moneda_origen', 'moneda_destino').order_by('-fecha_efectiva', 'moneda_origen__codigo_iso')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_tab'] = 'configuracion'
        context['title'] = 'Tasas de Cambio'
        # Obtener las últimas tasas únicas por par de monedas
        recientes = []
        pares_vistos = set()
        for t in self.get_queryset():
            par = (t.moneda_origen_id, t.moneda_destino_id)
            if par not in pares_vistos:
                recientes.append(t)
                pares_vistos.add(par)
            if len(recientes) >= 5:
                break
        context['tasas_actuales'] = recientes
        return context

class TipoCambioCreateView(SaaSMixin, LoginRequiredMixin, CreateView):
    model = TipoCambio
    template_name = 'core/config/tasas_form.html'
    fields = ['moneda_origen', 'moneda_destino', 'fecha_efectiva', 'tasa_conversion']
    success_url = reverse_lazy('core:tasas_list')

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        for field in form.fields.values():
            field.widget.attrs['class'] = 'w-full bg-white border border-gray-300 rounded-lg px-4 py-2.5 text-gray-900 focus:ring-primary focus:border-primary'
        return form

    def form_valid(self, form):
        messages.success(self.request, "Tasa de cambio registrada exitosamente.")
        return super().form_valid(form)

class SincronizarTasasActionView(LoginRequiredMixin, View):
    def post(self, request):
        try:
            # Reutilizamos la lógica existente en contabilidad
            sincronizar_tasas_manual(request)
            # El mensaje de éxito ya lo pone sincronizar_tasas_manual
        except Exception as e:
            messages.error(request, f"Error al sincronizar: {str(e)}")
        return redirect('core:tasas_list')

class ProveedorListView(SaaSMixin, LoginRequiredMixin, ListView):
    model = Proveedor
    template_name = 'core/erp/catalogos/proveedores_list.html'
    context_object_name = 'proveedores'
    paginate_by = 30
    
    def get_queryset(self):
        q = self.request.GET.get('q')
        queryset = Proveedor.objects.all().order_by('nombre')
        if q:
            queryset = queryset.filter(Q(nombre__icontains=q) | Q(rif__icontains=q) | Q(tipo_proveedor__icontains=q))
        return queryset

class ProveedorCreateView(SaaSMixin, LoginRequiredMixin, CreateView):
    model = Proveedor
    template_name = 'core/erp/catalogos/proveedores_form.html'
    fields = ['nombre', 'rif', 'tipo_proveedor', 'nivel_proveedor', 'contacto_nombre', 'contacto_email', 'contacto_telefono', 'direccion', 'ciudad', 'notas', 'numero_cuenta_agencia', 'condiciones_pago', 'datos_bancarios', 'activo']
    success_url = reverse_lazy('core:proveedores_list')

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        for field in form.fields.values():
            field.widget.attrs['class'] = 'w-full bg-white/5 border border-white/10 rounded-xl px-4 py-2 text-white focus:ring-2 focus:ring-blue-500 transition-all'
        return form

    def form_valid(self, form):
        messages.success(self.request, "Proveedor registrado exitosamente.")
        return super().form_valid(form)

class ProveedorUpdateView(SaaSMixin, LoginRequiredMixin, UpdateView):
    model = Proveedor
    template_name = 'core/erp/catalogos/proveedores_form.html'
    fields = ['nombre', 'rif', 'tipo_proveedor', 'nivel_proveedor', 'contacto_nombre', 'contacto_email', 'contacto_telefono', 'direccion', 'ciudad', 'notas', 'numero_cuenta_agencia', 'condiciones_pago', 'datos_bancarios', 'activo']
    success_url = reverse_lazy('core:proveedores_list')

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        for field in form.fields.values():
            field.widget.attrs['class'] = 'w-full bg-white/5 border border-white/10 rounded-xl px-4 py-2 text-white focus:ring-2 focus:ring-blue-500 transition-all'
        return form

    def form_valid(self, form):
        messages.success(self.request, "Proveedor actualizado exitosamente.")
        return super().form_valid(form)

class ProveedorDeleteView(SaaSMixin, LoginRequiredMixin, DeleteView):
    model = Proveedor
    template_name = 'core/erp/catalogos/proveedores_confirm_delete.html'
    success_url = reverse_lazy('core:proveedores_list')

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Proveedor eliminado correctamente.")
        return super().delete(request, *args, **kwargs)

# --- Comisiones ---

class ComisionProveedorServicioListView(SaaSMixin, LoginRequiredMixin, ListView):
    model = ComisionProveedorServicio
    template_name = 'core/erp/catalogos/comisiones_list.html'
    context_object_name = 'comisiones'
    paginate_by = 30
    
    def get_queryset(self):
        queryset = ComisionProveedorServicio.objects.select_related('proveedor', 'moneda').all().order_by('proveedor__nombre', 'tipo_servicio')
        proveedor_id = self.request.GET.get('proveedor')
        if proveedor_id:
            queryset = queryset.filter(proveedor_id=proveedor_id)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['proveedores'] = Proveedor.objects.all().order_by('nombre')
        context['proveedor_id'] = self.request.GET.get('proveedor')
        return context

class ComisionProveedorServicioCreateView(SaaSMixin, LoginRequiredMixin, CreateView):
    model = ComisionProveedorServicio
    template_name = 'core/erp/catalogos/comisiones_form.html'
    fields = ['proveedor', 'tipo_servicio', 'comision_porcentaje', 'comision_monto_fijo', 'moneda', 'notas', 'activo']
    success_url = reverse_lazy('core:comisiones_list')

    def get_initial(self):
        initial = super().get_initial()
        proveedor_id = self.request.GET.get('proveedor')
        if proveedor_id:
            initial['proveedor'] = proveedor_id
        return initial

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        for field in form.fields.values():
            field.widget.attrs['class'] = 'w-full bg-white/5 border border-white/10 rounded-xl px-4 py-2 text-white focus:ring-2 focus:ring-blue-500 transition-all'
        return form

    def form_valid(self, form):
        messages.success(self.request, "Regla de comisión creada exitosamente.")
        return super().form_valid(form)

class ComisionProveedorServicioUpdateView(SaaSMixin, LoginRequiredMixin, UpdateView):
    model = ComisionProveedorServicio
    template_name = 'core/erp/catalogos/comisiones_form.html'
    fields = ['proveedor', 'tipo_servicio', 'comision_porcentaje', 'comision_monto_fijo', 'moneda', 'notas', 'activo']
    success_url = reverse_lazy('core:comisiones_list')

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        for field in form.fields.values():
            field.widget.attrs['class'] = 'w-full bg-white/5 border border-white/10 rounded-xl px-4 py-2 text-white focus:ring-2 focus:ring-blue-500 transition-all'
        return form

    def form_valid(self, form):
        messages.success(self.request, "Regla de comisión actualizada exitosamente.")
        return super().form_valid(form)

class ComisionProveedorServicioDeleteView(SaaSMixin, LoginRequiredMixin, DeleteView):
    model = ComisionProveedorServicio
    template_name = 'core/erp/catalogos/comisiones_confirm_delete.html'
    success_url = reverse_lazy('core:comisiones_list')

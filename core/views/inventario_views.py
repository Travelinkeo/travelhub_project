from django.views.generic import ListView, CreateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.http import HttpResponse
from core.models.productos_terrestres import ProductoTerrestre
from core.middleware import get_current_agency

class CatalogoTerrestreListView(LoginRequiredMixin, ListView):
    """
    Vista principal del catálogo de inventario propio.
    Filtra los productos por la agencia actual (Multi-tenant).
    """
    model = ProductoTerrestre
    template_name = 'core/inventario/catalogo_terrestre.html'
    context_object_name = 'productos'

    def get_queryset(self):
        agency = get_current_agency()
        if agency:
            # El TenantManager ya filtra por agencia, pero somos explícitos aquí por claridad.
            return ProductoTerrestre.objects.filter(agencia=agency, activo=True)
        return ProductoTerrestre.objects.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = "Catálogo Terrestre"
        context['page_subtitle'] = "Inventario Propio"
        return context

class ProductoTerrestreCreateView(LoginRequiredMixin, CreateView):
    """
    Vista para crear un nuevo producto en el catálogo.
    Asigna automáticamente la agencia del usuario actual.
    """
    model = ProductoTerrestre
    fields = [
        'tipo_servicio', 'nombre', 'destino', 
        'descripcion_publica', 'costo_neto', 
        'markup_porcentaje', 'imagen_principal'
    ]
    success_url = reverse_lazy('core:catalogo_terrestre')

    def form_valid(self, form):
        agency = get_current_agency()
        if not agency:
            return HttpResponse("No se detectó una agencia activa en el contexto.", status=403)
        
        form.instance.agencia = agency
        # El precio_venta_calculado se calcula en el clean() o save() del modelo.
        return super().form_valid(form)

    def form_invalid(self, form):
        # Para depuración con HTMX o formularios complejos
        return super().form_invalid(form)

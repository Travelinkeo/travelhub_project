from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.db.models import Q, Sum
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.http import HttpResponse
from .models import Venta, ItemVenta, FeeVenta, PagoVenta
from core.mixins import SaaSMixin

class BookingBaseMixin(SaaSMixin, LoginRequiredMixin):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_tab'] = 'ventas'
        return context

# --- VENTAS ---

class VentaListView(BookingBaseMixin, ListView):
    model = Venta
    template_name = 'bookings/venta_list.html'
    context_object_name = 'ventas'
    paginate_by = 25

    def get_queryset(self):
        queryset = super().get_queryset().select_related('cliente', 'moneda').order_by('-fecha_venta')
        q = self.request.GET.get('q')
        if q:
            queryset = queryset.filter(
                Q(localizador__icontains=q) |
                Q(cliente__nombres__icontains=q) |
                Q(cliente__apellidos__icontains=q)
            )
        return queryset

class VentaDetailView(BookingBaseMixin, DetailView):
    model = Venta
    template_name = 'bookings/venta_detail_modern.html'
    context_object_name = 'venta'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['items'] = self.object.items_venta.all().select_related('producto_servicio', 'proveedor_servicio')
        context['fees'] = self.object.fees_venta.all()
        context['pagos'] = self.object.pagos_venta.all()
        return context

class VentaCreateView(BookingBaseMixin, CreateView):
    model = Venta
    template_name = 'bookings/venta_form.html'
    fields = ['cliente', 'moneda', 'tipo_venta', 'descripcion_general', 'notas']
    success_url = reverse_lazy('bookings:venta_list')

    def form_valid(self, form):
        messages.success(self.request, "Venta creada correctamente.")
        return super().form_valid(form)

class VentaUpdateView(BookingBaseMixin, UpdateView):
    model = Venta
    template_name = 'bookings/venta_form.html'
    fields = ['cliente', 'moneda', 'estado', 'tipo_venta', 'descripcion_general', 'notas']
    
    def get_success_url(self):
        return reverse_lazy('bookings:venta_detail', kwargs={'pk': self.object.pk})

class VentaDeleteView(BookingBaseMixin, DeleteView):
    model = Venta
    template_name = 'bookings/venta_confirm_delete.html'
    success_url = reverse_lazy('bookings:venta_list')

# --- HTMX INLINE ACTIONS ---

class ItemVentaCreateView(BookingBaseMixin, CreateView):
    model = ItemVenta
    template_name = 'bookings/partials/item_venta_form.html'
    fields = ['producto_servicio', 'descripcion_personalizada', 'cantidad', 'precio_unitario_venta', 'costo_neto_proveedor', 'proveedor_servicio']

    def form_valid(self, form):
        venta = get_object_or_404(Venta, pk=self.kwargs['venta_pk'])
        form.instance.venta = venta
        form.save()
        venta.recalcular_finanzas()
        
        if self.request.headers.get('HX-Request'):
            return render(self.request, 'bookings/partials/venta_totals_card.html', {'venta': venta})
        return redirect('bookings:venta_detail', pk=venta.pk)

class FeeVentaCreateView(BookingBaseMixin, CreateView):
    model = FeeVenta
    template_name = 'bookings/partials/feeventa_form.html'
    fields = ['tipo_fee', 'monto', 'descripcion']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['venta_pk'] = self.kwargs['venta_pk']
        return context

    def form_valid(self, form):
        venta = get_object_or_404(Venta, pk=self.kwargs['venta_pk'])
        form.instance.venta = venta
        form.save()
        venta.recalcular_finanzas()
        
        if self.request.headers.get('HX-Request'):
            return render(self.request, 'bookings/partials/venta_totals_card.html', {'venta': venta})
        return redirect('bookings:venta_detail', pk=venta.pk)

class PagoVentaCreateView(BookingBaseMixin, CreateView):
    model = PagoVenta
    template_name = 'bookings/partials/pagoventa_form.html'
    fields = ['monto', 'metodo_pago', 'referencia', 'comprobante']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['venta_pk'] = self.kwargs['venta_pk']
        return context

    def form_valid(self, form):
        venta = get_object_or_404(Venta, pk=self.kwargs['venta_pk'])
        form.instance.venta = venta
        form.save()
        venta.recalcular_finanzas()
        
        if self.request.headers.get('HX-Request'):
            return render(self.request, 'bookings/partials/venta_totals_card.html', {'venta': venta})
        return redirect('bookings:venta_detail', pk=venta.pk)

class ItemVentaUpdateView(BookingBaseMixin, UpdateView):
    model = ItemVenta
    template_name = 'bookings/partials/item_venta_form.html'
    fields = ['descripcion_personalizada', 'cantidad', 'precio_unitario_venta', 'costo_neto_proveedor']

    def form_valid(self, form):
        response = super().form_valid(form)
        self.object.venta.recalcular_finanzas()
        return response
    
    def get_success_url(self):
        return reverse_lazy('bookings:venta_detail', kwargs={'pk': self.object.venta.pk})

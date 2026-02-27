from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.urls import reverse_lazy
from django.shortcuts import redirect
from django.contrib import messages
from django.db import transaction

from cotizaciones.models import Cotizacion
from core.forms import CotizacionForm, ItemCotizacionFormSet

class CotizacionDashboardView(LoginRequiredMixin, ListView):
    model = Cotizacion
    template_name = 'core/erp/cotizaciones/dashboard.html'
    context_object_name = 'cotizaciones'
    paginate_by = 20

    def get_queryset(self):
        queryset = Cotizacion.objects.select_related('cliente', 'moneda').order_by('-fecha_emision')
        
        q = self.request.GET.get('q')
        if q:
            queryset = queryset.filter(
                Q(numero_cotizacion__icontains=q) |
                Q(cliente__nombres__icontains=q) |
                Q(cliente__apellidos__icontains=q) |
                Q(cliente__numero_documento__icontains=q)
            )
            
        estado = self.request.GET.get('estado')
        if estado:
            queryset = queryset.filter(estado=estado)
            
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Stats
        context['total_cotizaciones'] = Cotizacion.objects.count()
        context['cotizaciones_pendientes'] = Cotizacion.objects.filter(estado='BOR').count() # Borrador as pending
        context['cotizaciones_enviadas'] = Cotizacion.objects.filter(estado='ENV').count()
        return context

class CotizacionDetailView(LoginRequiredMixin, DetailView):
    model = Cotizacion
    template_name = 'core/erp/cotizaciones/detalle.html'
    context_object_name = 'cotizacion'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['items'] = self.object.items_cotizacion.all()
        return context

class CotizacionCreateView(LoginRequiredMixin, CreateView):
    model = Cotizacion
    form_class = CotizacionForm
    template_name = 'core/erp/cotizaciones/form.html'
    success_url = reverse_lazy('core:cotizacion_dashboard')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['items_formset'] = ItemCotizacionFormSet(self.request.POST)
        else:
            context['items_formset'] = ItemCotizacionFormSet()
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        items_formset = context['items_formset']
        with transaction.atomic():
            self.object = form.save()
            if items_formset.is_valid():
                items_formset.instance = self.object
                items_formset.save()
            else:
                return self.form_invalid(form)
        messages.success(self.request, f"Cotización {self.object.numero_cotizacion} creada exitosamente.")
        return super().form_valid(form)

class CotizacionUpdateView(LoginRequiredMixin, UpdateView):
    model = Cotizacion
    form_class = CotizacionForm
    template_name = 'core/erp/cotizaciones/form.html'
    
    def get_success_url(self):
        return reverse_lazy('core:cotizacion_detalle', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['items_formset'] = ItemCotizacionFormSet(self.request.POST, instance=self.object)
        else:
            context['items_formset'] = ItemCotizacionFormSet(instance=self.object)
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        items_formset = context['items_formset']
        with transaction.atomic():
            self.object = form.save()
            if items_formset.is_valid():
                items_formset.instance = self.object
                items_formset.save()
            else:
                return self.form_invalid(form)
        messages.success(self.request, f"Cotización {self.object.numero_cotizacion} actualizada exitosamente.")
        return super().form_valid(form)

from django.views import View
from django.shortcuts import get_object_or_404

class CotizacionStatusView(LoginRequiredMixin, View):
    def post(self, request, pk):
        cotizacion = get_object_or_404(Cotizacion, pk=pk)
        nuevo_estado = request.POST.get('nuevo_estado')
        
        # Validar transiciones permitidas
        permitido = False
        if cotizacion.estado == Cotizacion.EstadoCotizacion.BORRADOR and nuevo_estado == Cotizacion.EstadoCotizacion.ENVIADA:
            permitido = True
        elif cotizacion.estado == Cotizacion.EstadoCotizacion.ENVIADA and nuevo_estado in [Cotizacion.EstadoCotizacion.ACEPTADA, Cotizacion.EstadoCotizacion.RECHAZADA]:
            permitido = True
        elif cotizacion.estado == Cotizacion.EstadoCotizacion.RECHAZADA and nuevo_estado == Cotizacion.EstadoCotizacion.BORRADOR:
            # Opción para reabrir/restaurar
            permitido = True
            
        if permitido:
            cotizacion.estado = nuevo_estado
            cotizacion.save()
            messages.success(request, f"Estado actualizado a {cotizacion.get_estado_display()}.")
        else:
            messages.error(request, "Cambio de estado no permitido.")
            
        return redirect('core:cotizacion_detalle', pk=pk)

class CotizacionPDFView(LoginRequiredMixin, View):
    def get(self, request, pk):
        cotizacion = get_object_or_404(Cotizacion, pk=pk)
        try:
             # Importar servicio aquí para evitar ciclos si los hubiera
            from cotizaciones.pdf_service import generar_pdf_cotizacion
            pdf_bytes = generar_pdf_cotizacion(cotizacion)
            
            response = HttpResponse(pdf_bytes, content_type='application/pdf')
            filename = f"Cotizacion_{cotizacion.numero_cotizacion}.pdf"
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
        except Exception as e:
            messages.error(request, f"Error generando PDF: {str(e)}")
            return redirect('core:cotizacion_detalle', pk=pk)

class CotizacionConvertirView(LoginRequiredMixin, View):
    def post(self, request, pk):
        cotizacion = get_object_or_404(Cotizacion, pk=pk)
        
        try:
            with transaction.atomic():
                venta = cotizacion.convertir_a_venta()
                messages.success(request, f"Venta generada exitosamente: {venta.localizador}")
                return redirect('core:venta_detalle', pk=venta.pk)
        except ValueError as e:
            messages.warning(request, str(e))
        except Exception as e:
            messages.error(request, f"Error al convertir a venta: {str(e)}")
            
        return redirect('core:cotizacion_detalle', pk=pk)

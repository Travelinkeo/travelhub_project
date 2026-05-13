from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, Sum
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from apps.bookings.models import BoletoImportado, FeeVenta, Venta
from apps.crm.models import Cliente
from core.forms import FeeVentaForm
from core.mixins import HtmxResponseMixin, SaaSMixin
from core.security import get_agencia_or_403, get_object_tenant_or_404, get_user_active_agency


class VentaUpdateView(SaaSMixin, LoginRequiredMixin, UpdateView):
    model = Venta
    template_name = 'core/venta_edit_glass_v2.html'
    fields = ['cliente', 'localizador', 'estado']
    fields = ['cliente', 'localizador', 'estado']
    # success_url = reverse_lazy('core:modern_dashboard') # Overridden by get_success_url

    def get_success_url(self):
        # Support for 'next' parameter to return to Admin or specific page
        next_url = self.request.GET.get('next') or self.request.POST.get('next')
        if next_url:
            return next_url
        return reverse_lazy('core:modern_dashboard')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Pass 'next' to template to preserve it in POST
        context['next'] = self.request.GET.get('next')
        # Pasar el primer item para pre-llenar los inputs manuales (con select_related)
        context['first_item'] = self.object.items_venta.select_related(
            'producto_servicio', 'moneda'
        ).first()
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        
        # Actualizar datos del Item (Financieros) - usar select_related
        item = self.object.items_venta.select_related(
            'producto_servicio', 'moneda'
        ).first()
        if item:
            try:
                precio = self.request.POST.get('item_precio')
                costo = self.request.POST.get('item_costo')
                comision = self.request.POST.get('item_comision')
                
                if precio: item.precio_unitario_venta = precio
                if costo: item.costo_neto_proveedor = costo
                if comision: item.comision_agencia_monto = comision
                
                # Recalcular totales del item
                item.impuestos_item_venta = 0 # Simplificación por ahora
                item.save()
                
                # Recalcular Venta desde Servicio
                from apps.finance.services.finance_service import FinanceService
                FinanceService.recalculate_sale_finances(self.object.pk)
                
            except Exception as e:
                # Log error but don't crash
                print(f"Error actualizando item: {e}")
                
        return response


class VentasDashboardView(HtmxResponseMixin, SaaSMixin, LoginRequiredMixin, ListView):
    model = Venta
    template_name = 'core/erp/ventas/dashboard.html'
    htmx_template_name = 'bookings/partials/venta_list_htmx.html'
    context_object_name = 'ventas'
    paginate_by = 20

    def get_queryset(self):
        # SaaSMixin filters by agency first
        queryset = super().get_queryset()
        queryset = queryset.select_related('cliente', 'moneda').order_by('-fecha_venta')
        
        # Search
        q = self.request.GET.get('q')
        if q:
            queryset = queryset.filter(
                Q(localizador__icontains=q) |
                Q(cliente__nombres__icontains=q) |
                Q(cliente__apellidos__icontains=q) |
                Q(id_venta__icontains=q)
            )
            
        # Filters
        estado = self.request.GET.get('estado')
        if estado:
            queryset = queryset.filter(estado=estado)
            
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_tab'] = 'ventas'
        
        # Stats for the dashboard header (Filtered by Agency)
        # We reconstruct the base queryset for the agency to avoid applying search filters to stats
        base_qs = Venta.objects.select_related('cliente', 'moneda', 'agencia')
        agencia = get_user_active_agency(self.request.user)
        if agencia:
            base_qs = base_qs.filter(agencia=agencia)
        
        context['total_ventas_mes'] = base_qs.count()  # Simplified for POC
        context['monto_total_mes'] = base_qs.aggregate(Sum('total_venta'))['total_venta__sum'] or 0
        context['pendientes_pago'] = base_qs.filter(estado='PEN').count()
        
        return context

class VentaCreateView(SaaSMixin, LoginRequiredMixin, CreateView):
    model = Venta
    template_name = 'core/erp/ventas/form.html'
    fields = ['cliente', 'moneda', 'estado']
    success_url = reverse_lazy('core:ventas_dashboard')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_tab'] = 'ventas'
        context['title'] = 'Nueva Venta'
        return context

class VentaDetailView(HtmxResponseMixin, SaaSMixin, LoginRequiredMixin, DetailView):
    model = Venta
    template_name = 'core/erp/ventas/detalle_final.html'
    # Esta es la magia reactiva: si HTMX pide la vista, devolvemos solo este fragmento
    htmx_template_name = 'ventas/partials/detalle_htmx.html'
    context_object_name = 'venta'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_tab'] = 'ventas'
        
        # Related objects - Optimized with select_related and prefetch_related
        context['boletos'] = BoletoImportado.objects.filter(
            venta_asociada=self.object
        ).select_related('proveedor', 'agencia', 'moneda')
        
        context['items'] = self.object.items_venta.select_related(
            'producto_servicio', 'moneda'
        ).all()
        
        context['pagos'] = self.object.pagos_venta.select_related(
            'moneda', 'metodo_pago'
        ).all()
        
        # 🧠 Sales Intelligence AI
        from apps.automation.services.ai_parser_service import AIParserService
        ai_tips = []
        
        # Analizar boletos para obtener tips reales
        for boleto in context['boletos']:
            # Simular data para el analizador (luego esto vendrá de un JSON field)
            mock_data = {
                "boletos": [{
                    "itinerario": [
                        {"origen": boleto.origen, "destino": boleto.destino}
                    ]
                }]
            }
            ai_tips.extend(AIParserService.analyze_sales_opportunities(mock_data))
        
        context['ai_tips'] = list(set(ai_tips))[:3] # Max 3 tips únicos
        
        return context

from django.contrib import messages
from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect


class VentaAssignClientView(LoginRequiredMixin, View):
    def post(self, request, pk):
        # 🔐 CANDADO: Solo accede a ventas de la agencia del usuario.
        agencia = get_agencia_or_403(request)
        venta = get_object_tenant_or_404(Venta, agencia, pk=pk)
        cliente_id = request.POST.get('cliente_id')
        
        if cliente_id:
            cliente = get_object_or_404(Cliente, pk=cliente_id)
            venta.cliente = cliente
            venta.save()
            messages.success(request, f"Cliente {cliente} asignado correctamente.")
        else:
            messages.error(request, "Debe seleccionar un cliente.")
            
        return redirect('core:venta_detalle', pk=pk)

class VentaAddFeeView(LoginRequiredMixin, CreateView):
    model = FeeVenta
    form_class = FeeVentaForm
    template_name = 'core/erp/ventas/fee_form.html'

    def dispatch(self, request, *args, **kwargs):
        # 🔐 CANDADO: Solo accede a ventas de la agencia del usuario.
        agencia = get_agencia_or_403(request)
        self.venta = get_object_tenant_or_404(Venta, agencia, pk=self.kwargs['pk'])
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        fee = form.save(commit=False)
        fee.venta = self.venta
        fee.save()
        # self.venta.recalcular_finanzas()
        from apps.finance.services.finance_service import FinanceService
        FinanceService.recalculate_sale_finances(self.venta.pk)
        messages.success(self.request, "Fee registrado exitosamente.")
        return redirect('core:venta_detalle', pk=self.venta.pk)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['venta'] = self.venta
        return context

class VentaGenerateInvoiceView(LoginRequiredMixin, View):
    def post(self, request, pk):
        # 🔒 CANDADO: Solo accede a ventas de la agencia del usuario.
        agencia = get_agencia_or_403(request)
        venta = get_object_tenant_or_404(Venta, agencia, pk=pk)

        try:
            from apps.finance.services.invoicing_service import InvoicingService
            factura = InvoicingService.create_invoice_from_venta(venta.pk, agencia)
            messages.success(request, f"Factura #{factura.numero_factura} generada exitosamente.")
        except DjangoValidationError as e:
            messages.warning(request, str(e))
        except Exception as e:
            import logging
            logging.getLogger(__name__).exception("Error en VentaGenerateInvoiceView")
            messages.error(request, f"Error al generar factura: {str(e)}")

        return redirect('core:venta_detalle', pk=pk)

class VentaGenerateVoucherView(LoginRequiredMixin, View):
    def get(self, request, pk):
        # 🔐 CANDADO: Solo accede a ventas de la agencia del usuario.
        agencia = get_agencia_or_403(request)
        venta = get_object_tenant_or_404(Venta, agencia, pk=pk)
        
        try:
            from apps.bookings.services.voucher_service import generar_voucher_unificado
            pdf_bytes, filename = generar_voucher_unificado(venta.pk)
            
            if pdf_bytes:
                response = HttpResponse(pdf_bytes, content_type='application/pdf')
                response['Content-Disposition'] = f'attachment; filename="{filename}"'
                return response
            else:
                messages.error(request, "No se pudo generar el PDF del voucher.")
        except Exception as e:
            messages.error(request, f"Error al generar voucher: {str(e)}")
            
        return redirect('core:venta_detalle', pk=pk)

@login_required
def eliminar_venta(request, pk):
    """🗑️ Eliminación física de una venta y sus ítems."""
    agencia = get_agencia_or_403(request)
    # Buscamos con all_objects por si estuviera soft-deleted
    venta = get_object_tenant_or_404(Venta.all_objects, agencia, pk=pk)
    
    try:
        # Borrar físicamente (HARD DELETE)
        # Esto borrará también items, segmentos, pagos, etc (por CASCADE en DB)
        venta.delete(force=True)
        messages.success(request, f"Venta {pk} eliminada físicamente con éxito.")
    except Exception as e:
        messages.error(request, f"Error al eliminar venta: {str(e)}")
        
    next_url = request.GET.get('next') or 'core:modern_dashboard'
    return redirect(next_url)

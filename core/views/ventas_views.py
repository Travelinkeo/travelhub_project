from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, Sum
from django.urls import reverse_lazy
from core.models import Proveedor
from apps.bookings.models import Venta, BoletoImportado, ItemVenta, FeeVenta
from core.forms import FeeVentaForm

from apps.crm.models import Cliente
from core.mixins import SaaSMixin
from core.security import get_agencia_or_403, get_object_tenant_or_404

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
        # Pasar el primer item para pre-llenar los inputs manuales
        context['first_item'] = self.object.items_venta.first()
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        
        # Actualizar datos del Item (Financieros)
        item = self.object.items_venta.first()
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
                
                # Recalcular Venta
                self.object.recalcular_finanzas()
                
            except Exception as e:
                # Log error but don't crash
                print(f"Error actualizando item: {e}")
                
        return response


class VentasDashboardView(SaaSMixin, LoginRequiredMixin, ListView):
    model = Venta
    template_name = 'core/erp/ventas/dashboard.html'
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
        base_qs = Venta.objects.all()
        user = self.request.user
        if not user.is_superuser and hasattr(user, 'agencias'):
            ua = user.agencias.filter(activo=True).first()
            if ua:
                base_qs = base_qs.filter(agencia=ua.agencia)
        
        context['total_ventas_mes'] = base_qs.count() # Simplified for POC
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

class VentaDetailView(SaaSMixin, LoginRequiredMixin, DetailView):
    model = Venta
    template_name = 'core/erp/ventas/detalle_final.html'
    context_object_name = 'venta'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_tab'] = 'ventas'
        
        # Related objects
        context['boletos'] = BoletoImportado.objects.filter(venta_asociada=self.object)
        context['items'] = self.object.items_venta.all()
        context['pagos'] = self.object.pagos_venta.all()
        
        # 🧠 Sales Intelligence AI
        from core.services.ai_parser_service import AIParserService
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

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views import View
from django.contrib import messages
from apps.bookings.models import Venta
from django.http import HttpResponse
from apps.finance.models import Factura, ItemFactura

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
        self.venta.recalcular_finanzas()
        messages.success(self.request, f"Fee registrado exitosamente.")
        return redirect('core:venta_detalle', pk=self.venta.pk)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['venta'] = self.venta
        return context

class VentaGenerateInvoiceView(LoginRequiredMixin, View):
    def post(self, request, pk):
        # 🔐 CANDADO: Solo accede a ventas de la agencia del usuario.
        agencia = get_agencia_or_403(request)
        venta = get_object_tenant_or_404(Venta, agencia, pk=pk)
        
        if not venta.cliente:
            messages.error(request, "La venta debe tener un cliente asignado para facturar.")
            return redirect('core:venta_detalle', pk=pk)
            
        if hasattr(venta, 'factura'):
            messages.warning(request, "Esta venta ya tiene una factura asociada.")
            return redirect('core:venta_detalle', pk=pk)
            
        try:
            # Create Invoice
            factura = Factura.objects.create(
                cliente=venta.cliente,
                moneda=venta.moneda,
                subtotal=venta.subtotal,
                monto_impuestos=venta.impuestos,
                venta_asociada=venta
            )

            # Calculate total fees to distribute/hide
            total_fees = venta.fees_venta.aggregate(Sum('monto'))['monto__sum'] or 0

            # Copy Items
            items_procesados = 0
            total_items = venta.items_venta.count()

            for item_venta in venta.items_venta.all():
                descripcion = item_venta.descripcion_personalizada or item_venta.producto_servicio.nombre
                
                # Enrich description logic (simplified from admin)
                if not item_venta.descripcion_personalizada and item_venta.producto_servicio.tipo_producto == 'AIR':
                    boleto = BoletoImportado.objects.filter(venta_asociada=venta).first()
                    if boleto:
                        descripcion = f"Boleto Aéreo: {boleto.ruta_vuelo or ''}"
                        if boleto.numero_boleto:
                            descripcion += f" ({boleto.numero_boleto})"

                precio_unitario = item_venta.precio_unitario_venta
                
                # LOGICA DE FEES OCULTOS:
                # Sumar todos los fees al PRIMER item de la factura (o distribuir, pero sumar al primero es más simple/común)
                if items_procesados == 0 and total_items > 0:
                    # Sumamos el total de fees al precio de este primer item
                    # Nota: Esto asume que el fee está en la misma moneda que la venta.
                    precio_unitario += total_fees

                ItemFactura.objects.create(
                    factura=factura,
                    descripcion=descripcion,
                    cantidad=item_venta.cantidad,
                    precio_unitario=precio_unitario, # Precio aumentado
                    tipo_servicio=item_venta.producto_servicio.tipo_producto,
                    es_gravado=False # Default assumption, should be refined
                )
                items_procesados += 1
                
            factura.save() # Recalculate totals
            messages.success(request, f"Factura #{factura.numero_factura} generada exitosamente. (Incluye Fees ocultos: {total_fees})")
            
        except Exception as e:
            messages.error(request, f"Error al generar factura: {str(e)}")
            
        return redirect('core:venta_detalle', pk=pk)

class VentaGenerateVoucherView(LoginRequiredMixin, View):
    def get(self, request, pk):
        # 🔐 CANDADO: Solo accede a ventas de la agencia del usuario.
        agencia = get_agencia_or_403(request)
        venta = get_object_tenant_or_404(Venta, agencia, pk=pk)
        
        try:
            from core.services.pdf_service import generar_pdf_voucher_unificado
            pdf_bytes, filename = generar_pdf_voucher_unificado(venta.pk)
            
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
    from core.security import get_agencia_or_403, get_object_tenant_or_404
    
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

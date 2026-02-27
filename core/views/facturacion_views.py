from django.views.generic import ListView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.urls import reverse
from django.db.models import Q
from django.http import HttpResponse

from core.models import Venta
from apps.finance.models import Factura
from core.services.facturacion_service import FacturacionService
from apps.crm.models import Cliente

class FacturacionDashboardView(LoginRequiredMixin, ListView):
    model = Factura
    template_name = 'core/erp/facturacion/dashboard.html'
    context_object_name = 'facturas'
    paginate_by = 20

    def get_queryset(self):
        queryset = Factura.objects.select_related('cliente', 'moneda').order_by('-fecha_emision')
        
        q = self.request.GET.get('q')
        if q:
            queryset = queryset.filter(
                Q(numero_factura__icontains=q) |
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
        # Stats simples
        context['total_facturas'] = Factura.objects.count()
        context['facturas_pendientes'] = Factura.objects.filter(estado='PEN').count()
        return context

class FacturaDetailView(LoginRequiredMixin, DetailView):
    model = Factura
    template_name = 'core/erp/facturacion/detalle.html'
    context_object_name = 'factura'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['items'] = self.object.items_factura.all()
        return context

def generar_factura_desde_venta(request, pk):
    """
    Vista para generar una factura desde una venta.
    Si la venta ya tiene cliente, genera la factura directo.
    Si no, redirige a una selección de cliente (simplificado por ahora: requiere cliente en venta).
    """
    venta = get_object_or_404(Venta, pk=pk)
    
    if venta.factura:
        messages.warning(request, f"La venta {venta.localizador or venta.pk} ya tiene una factura asociada.")
        return redirect('core:venta_detalle', pk=pk)
        
    if not venta.cliente:
        messages.error(request, "La venta debe tener un cliente asignado para poder facturar.")
        return redirect('core:venta_detalle', pk=pk)

    try:
        factura = FacturacionService.generar_factura_desde_venta(venta, venta.cliente)
        
        if request.headers.get('HX-Request'):
            # Return partial for the modal
            from django.shortcuts import render
            return render(request, 'finance/partials/invoice_detail_modal.html', {'invoice': factura})
            
        messages.success(request, f"Factura {factura.numero_factura} generada exitosamente.")
        return redirect('core:factura_detalle', pk=factura.pk)
    except Exception as e:
        error_msg = f"Error al generar la factura: {e}"
        if request.headers.get('HX-Request'):
            return HttpResponse(f'<div class="p-4 bg-red-900/20 text-red-400 rounded-xl border border-red-900/50">{error_msg}</div>', status=500)
        messages.error(request, error_msg)
        return redirect('core:venta_detalle', pk=pk)

def descargar_pdf_factura(request, pk):
    factura = get_object_or_404(Factura, pk=pk)
    if factura.archivo_pdf:
        response = HttpResponse(factura.archivo_pdf, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{factura.archivo_pdf.name}"'
        return response
    else:
        messages.error(request, "El PDF de esta factura no está disponible.")
        return redirect('core:factura_detalle', pk=pk)

def emitir_factura_definitiva(request, pk):
    """
    Cambia el estado de una factura de BORRADOR a EMITIDA.
    """
    factura = get_object_or_404(Factura, pk=pk)
    
    if factura.estado != Factura.EstadoFactura.BORRADOR:
        messages.warning(request, f"La factura {factura.numero_factura} ya no está en borrador.")
        return redirect('core:factura_detalle', pk=pk)
        
    try:
        # Lógica de emisión
        factura.estado = Factura.EstadoFactura.EMITIDA
        # Aquí se podría asignar un número de control fiscal real si fuese necesario
        factura.save()
        
        messages.success(request, f"Factura {factura.numero_factura} emitida correctamente.")
        return redirect('core:factura_detalle', pk=pk)
    except Exception as e:
        messages.error(request, f"Error al emitir factura: {e}")
        return redirect('core:factura_detalle', pk=pk)

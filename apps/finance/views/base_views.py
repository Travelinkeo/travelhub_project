import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import DetailView, ListView, TemplateView, View

from apps.contabilidad.services import ContabilidadService
from apps.finance.models import Factura
from apps.finance.models.reconciliacion import (
    ConciliacionBoleto,
    LineaReporteReconciliacion,
    ReporteReconciliacion,
)
from apps.finance.models.core_finance import (
    DiferenciaFinanciera,
    ReporteProveedor,
)
from apps.finance.services.analytics_service import FinancialAnalyticsService
from apps.finance.services.smart_reconciliation_service import SmartReconciliationService

logger = logging.getLogger(__name__)

class InvoiceListView(LoginRequiredMixin, ListView):
    model = Factura
    template_name = 'finance/invoice_list.html'
    context_object_name = 'invoices'
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset()
        estado = self.request.GET.get('estado')
        if estado:
            qs = qs.filter(estado=estado)
        return qs.select_related('cliente', 'agencia').order_by('-fecha_emision', '-id_factura')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filtros'] = {
            'estado': self.request.GET.get('estado', '')
        }
        return context

class InvoiceDetailView(LoginRequiredMixin, DetailView):
    model = Factura
    template_name = 'finance/partials/invoice_detail_modal.html'
    context_object_name = 'invoice'
    pk_url_kwarg = 'pk'

    def get(self, request, *args, **kwargs):
        # Si es una petición HTMX, devolvemos el partial
        if request.headers.get('HX-Request'):
            return super().get(request, *args, **kwargs)
        # Si no, redirigimos al listado (o podríamos tener una página dedicada)
        return redirect('finance:invoice_list')

class InvoiceIssueView(LoginRequiredMixin, View):
    """
    Cambia el estado de la factura de BORRADOR a EMITIDA.
    """
    def post(self, request, pk):
        factura = get_object_or_404(Factura, pk=pk)
        if factura.estado == Factura.EstadoFactura.BORRADOR:
            factura.estado = Factura.EstadoFactura.EMITIDA
            # Aquí se podría disparar la generación real del PDF fiscal o el envío a un PAC
            factura.save()
            
            # --- AGREGAR ASIENTO CONTABLE ---
            try:
                ContabilidadService.generar_asiento_desde_factura(factura)
            except Exception as e:
                logger.error(f"Error generando asiento contable para factura {factura.pk}: {e}")
                # Opcional: Podrías revertir la emisión si la contabilidad es crítica
                # factura.estado = Factura.EstadoFactura.BORRADOR
                # factura.save()
                # return HttpResponse(f"Error en contabilidad: {e}", status=500)
            
            if request.headers.get('HX-Request'):
                # Devolvemos una fila actualizada o un snippet de éxito
                return render(request, 'finance/partials/invoice_row.html', {'invoice': factura})
            
            return redirect('finance:invoice_list')
        
        return HttpResponse("Solo se pueden emitir facturas en borrador.", status=400)

class InvoiceUpdateView(LoginRequiredMixin, View):
    """
    Permite actualizaciones rápidas de campos no críticos en el borrador.
    """
    def post(self, request, pk):
        factura = get_object_or_404(Factura, pk=pk)
        if factura.estado == Factura.EstadoFactura.BORRADOR:
            # Ejemplo: actualizar notas
            notas = request.POST.get('notas')
            if notas is not None:
                factura.notas = notas
                factura.save()
            
            return HttpResponse("Factura actualizada", status=200)
        return HttpResponse("No se puede editar una factura emitida.", status=400)

# --- RECONCILIACIÓN ---

class ReportListView(LoginRequiredMixin, ListView):
    model = ReporteReconciliacion
    template_name = 'finance/reconciliation/report_list.html'
    context_object_name = 'reports'
    ordering = ['-fecha_subida']

    def get_queryset(self):
        return super().get_queryset().select_related('agencia')

class ReportUploadView(LoginRequiredMixin, View):
    def post(self, request):
        from apps.finance.services.smart_reconciliation_service import SmartReconciliationService

        proveedor = request.POST.get('proveedor', 'Desconocido')
        archivo = request.FILES.get('archivo')

        if not archivo:
            return HttpResponse("Faltan campos obligatorios", status=400)

        reporte = ReporteReconciliacion.objects.create(
            agencia=request.agencia,
            archivo=archivo,
            proveedor=proveedor,
            estado='PENDIENTE'
        )

        try:
            SmartReconciliationService.procesar_reporte(str(reporte.id_reporte))
            return redirect('finance:report_detail', pk=reporte.pk)
        except Exception as e:
            logger.error(f"Error procesando reporte: {e}")
            return HttpResponse(f"Error procesando: {str(e)}", status=500)

class ReconciliationDetailView(LoginRequiredMixin, DetailView):
    model = ReporteReconciliacion
    template_name = 'finance/reconciliation/report_detail.html'
    context_object_name = 'report'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['lineas'] = self.object.lineas.all().order_by('numero_boleto_reportado')
        context['conciliaciones'] = self.object.conciliaciones.all().select_related('boleto_local').order_by('estado')
        return context

class ResolveDiscrepancyAIView(LoginRequiredMixin, View):
    """
    Endpoint HTMX para obtener sugerencia de la IA.
    """
    def get(self, request, pk):
        conciliacion = get_object_or_404(ConciliacionBoleto, pk=pk)

        suggestion = conciliacion.ia_razonamiento or "Sin sugerencia de IA disponible."

        return render(request, 'finance/reconciliation/partials/ai_suggestion.html', {
            'suggestion': suggestion,
            'diff': conciliacion
        })

class ProfitabilityDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'finance/profitability_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['metrics'] = FinancialAnalyticsService.get_real_time_metrics()
        context['monthly_stats'] = FinancialAnalyticsService.get_monthly_profitability()
        context['category_stats'] = FinancialAnalyticsService.get_profit_by_category()
        return context

class ProfitSeriesDataView(LoginRequiredMixin, View):
    def get(self, request):
        data = FinancialAnalyticsService.get_monthly_profitability()
        return JsonResponse(data, safe=False)

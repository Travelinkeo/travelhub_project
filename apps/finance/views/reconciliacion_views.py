from django.views.generic import TemplateView, CreateView, DetailView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from apps.finance.models.reconciliacion import ReporteReconciliacion, ConciliacionBoleto
from django.db.models import Sum, Count, Q
from django.urls import reverse_lazy
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from apps.finance.forms import ReporteReconciliacionForm
from apps.finance.services.smart_reconciliation_service import SmartReconciliationService


class ReconciliationDashboardHTMXView(LoginRequiredMixin, TemplateView):
    """
    Dashboard unificado para ver el estatus de todos los cruces de proveedores
    (Amadeus, Sabre, KIU, etc.) contra nuestras ventas reportadas.
    """
    template_name = 'finance/reconciliacion/dashboard_htmx.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Últimos 10 reportes cargados
        reportes = ReporteReconciliacion.objects.select_related('agencia').order_by('-fecha_subida')[:10]
        context['ultimos_reportes'] = reportes
        
        # Métrica Global Acelerada (Podría filtrarse por agencia en multitenant)
        stats = ConciliacionBoleto.objects.aggregate(
            total_discrepancias=Count('id_conciliacion', filter=~Q(estado='OK')),
            perdida_detectada_usd=Sum('diferencia_total', filter=Q(diferencia_total__gt=0)),
            ahorro_detectado_usd=Sum('diferencia_total', filter=Q(diferencia_total__lt=0)),
            asientos_generados=Count('sugerencia_asiento')
        )
        
        context['stats_globales'] = {
            'discrepancias': stats['total_discrepancias'] or 0,
            'perdidas': (stats['perdida_detectada_usd'] or 0),
            'ahorros': abs(stats['ahorro_detectado_usd'] or 0),
            'asientos_borrador': stats['asientos_generados'] or 0
        }
        
        # Conciliaciones Críticas (Las de mayor pérdida)
        context['alertas_criticas'] = ConciliacionBoleto.objects.filter(
            diferencia_total__gt=5  # Hardcoded. Podria ser configurable. Mostrar diferencias > 5 USD
        ).select_related('reporte', 'linea_reporte', 'boleto_local').order_by('-diferencia_total')[:15]
        
        return context


class ReporteReconciliacionCreateView(LoginRequiredMixin, CreateView):
    """
    Vista Frontend que reemplaza la subida desde el Django Admin original del Sistema de Contaduría.
    Muestra la UI adaptada del modal HTMX.
    """
    model = ReporteReconciliacion
    form_class = ReporteReconciliacionForm
    template_name = 'finance/reconciliacion/reporte_form.html'
    
    def form_valid(self, form):
        # Aseguramos el tenant agency (Hardcode a la primera temporalmente)
        from core.models import Agencia
        form.instance.agencia = Agencia.objects.first()
        messages.success(self.request, "Reporte sincronizado de manera exitosa. Listo para ser cruzado a nivel contable.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('finance:reconciliacion_detail', kwargs={'pk': self.object.pk})


class ReporteReconciliacionDetailView(LoginRequiredMixin, DetailView):
    """
    Página de Desglose de cada documento, listando todas las discrepancias 
    y cruces realizados sobre ese archivo sin visitar el ActionAdmin.
    """
    model = ReporteReconciliacion
    template_name = 'finance/reconciliacion/reporte_detail.html'
    context_object_name = 'reporte'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Traer boletos conciliados de este reporte específico
        context['conciliaciones_lines'] = self.object.conciliaciones.select_related(
            'linea_reporte', 'boleto_local', 'sugerencia_asiento'
        ).order_by('-diferencia_total')
        return context


class ProcessReconciliacionHTMXView(LoginRequiredMixin, View):
    """
    Botón "Procesar con IA": invoca el servicio en background de Gemini Pro 
    y redirige a la vista completa del Detail tras concluir la ejecución HTMX.
    """
    def get(self, request, *args, **kwargs):
        # Allow GET for simplicity, normally POST is better for actions
        reporte_id = self.kwargs.get('pk')
        reporte = get_object_or_404(ReporteReconciliacion, pk=reporte_id)
        
        try:
            SmartReconciliationService.procesar_reporte(reporte_id)
            messages.success(request, f"¡Reporte analizado con inteligencia artificial y cruzado estadísticamente con éxito!")
        except Exception as e:
            messages.error(request, f"Error descifrando el documento GDS con IA: {str(e)}")
            
        return redirect('finance:reconciliacion_detail', pk=reporte_id)

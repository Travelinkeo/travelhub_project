import logging
from django.views.generic import DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Sum, Q
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404
from django.utils import timezone

from apps.finance.models.reconciliacion import ReporteReconciliacion, ConciliacionBoleto
from apps.finance.services.accounting_ai_service import AccountingAIService

logger = logging.getLogger(__name__)

class ReconciliationResultsView(LoginRequiredMixin, DetailView):
    """
    Pilar 4: Estación Final de Auditoría.
    Muestra los KPIs y la tabla interactiva de decisiones contables.
    """
    model = ReporteReconciliacion
    template_name = 'finance/reconciliacion/audit_results.html'
    context_object_name = 'reporte'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        reporte = self.object
        
        # 1. Cálculo de KPIs en tiempo real (Auditoría Forense)
        stats = reporte.conciliaciones.aggregate(
            total=Count('id_conciliacion'),
            matches=Count('id_conciliacion', filter=Q(estado='OK')),
            discrepancias=Count('id_conciliacion', filter=Q(estado='DISCREPANCIA')),
            huerfanos_proveedor=Count('id_conciliacion', filter=Q(estado='HUERFANO_PROVEEDOR')),
            huerfanos_local=Count('id_conciliacion', filter=Q(estado='HUERFANO_LOCAL')),
            monto_ajuste_neto=Sum('diferencia_total')
        )
        
        context['kpis'] = {
            'total': stats['total'] or 0,
            'matches': stats['matches'] or 0,
            'discrepancias': stats['discrepancias'] or 0,
            'alertas': (stats['huerfanos_proveedor'] or 0) + (stats['huerfanos_local'] or 0),
            'monto_ajuste': stats['monto_ajuste_neto'] or 0
        }

        # 2. Lista de Discrepancias para la Tabla Accionable
        # Filtramos 'OK' porque el auditor solo necesita ver problemas.
        context['discrepancias'] = reporte.conciliaciones.exclude(
            estado='OK'
        ).select_related('linea_reporte', 'boleto_local', 'sugerencia_asiento').order_by('-diferencia_total')
        
        return context

def approve_adjustment_htmx(request, conciliacion_id):
    """
    Pilar 3: One-Click Accounting (HTMX Endpoint).
    Ejecuta el asiento contable real basado en la sugerencia de la IA.
    """
    if request.method != 'POST':
        return HttpResponse("Método no permitido", status=405)

    conciliacion = get_object_or_404(ConciliacionBoleto, pk=conciliacion_id)
    
    # 1. Preparar contexto para el CPA Engine
    descripcion = f"Ajuste Auditoría: {conciliacion.linea_reporte.numero_boleto_reportado if conciliacion.linea_reporte else 'Boleto Interno'}"
    context_details = {
        'hallazgo': conciliacion.estado,
        'diferencia_monto': float(conciliacion.diferencia_total),
        'razonamiento_ia': conciliacion.ia_razonamiento,
        'reporte_ref': str(conciliacion.reporte.id_reporte)
    }

    # 2. Generar el Asiento Físico
    asiento = AccountingAIService.generar_asiento_con_ia(descripcion, context_details)
    
    if asiento:
        # 3. Actualizar estado de la conciliación
        conciliacion.sugerencia_asiento = asiento
        conciliacion.resolucion_notas = f"Auditado y aprobado por {request.user.username} (IA Certified)"
        conciliacion.save()
        
        # 4. Devolver fragmento de éxito (Banner verde)
        return render(request, 'finance/reconciliacion/partials/adjustment_success.html', {
            'asiento_id': asiento.id_asiento,
            'numero_asiento': f"AS-{asiento.id_asiento}"
        })
    else:
        # Si falla el motor contable por descuadre
        return HttpResponse('<span class="text-status-danger text-[10px] font-bold p-2 bg-status-danger-bg rounded">Falla CPA Engine</span>')

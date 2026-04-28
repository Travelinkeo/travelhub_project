import logging
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse
from celery.result import AsyncResult

from apps.finance.models.reconciliacion import ReporteReconciliacion
from apps.finance.tasks_reconciliation import conciliar_reporte_batch_task
from core.utils.celery_utils import safe_delay

logger = logging.getLogger(__name__)

class ReconciliationUploadView(LoginRequiredMixin, TemplateView):
    """
    Pilar 1: Vista de Subida Principal.
    Layout limpio para arrastrar el reporte del proveedor.
    """
    template_name = 'finance/reconciliacion/reconciliacion_upload.html'

def process_reconciliation_upload_htmx(request):
    """
    Pilar 3: Controlador de Subida HTMX.
    Recibe el archivo, lanza la IA en Celery y devuelve el monitor.
    """
    if request.method != 'POST':
        return HttpResponse("Método no permitido", status=405)

    try:
        archivo = request.FILES.get('archivo_reporte')
        proveedor = request.POST.get('proveedor', 'GDS_GENERIC')
        
        if not archivo:
            return HttpResponse('<p class="text-status-danger text-xs font-bold">Error: No se recibió ningún archivo.</p>')

        # 1. Crear el registro del reporte (Estado Inicial)
        # Asumimos que request.user.agencia está disponible (estándar TravelHub)
        reporte = ReporteReconciliacion.objects.create(
            agencia=request.user.agencia,
            archivo=archivo,
            proveedor=proveedor,
            estado='PENDIENTE'
        )

        # 2. Lanzar Tarea de Celery (Motor Híbrido IA)
        task_id = safe_delay(
            conciliar_reporte_batch_task,
            reporte_id=str(reporte.id_reporte),
            agencia_id=request.user.agencia.pk
        )

        if not task_id:
            reporte.estado = 'ERROR'
            reporte.error_log = "Celery no disponible."
            reporte.save()
            return HttpResponse('<p class="text-status-danger text-xs font-bold">Error: El motor de IA no está disponible.</p>')

        # 3. Devolver el monitor de progreso inicial
        context = {
            'task_id': task_id,
            'reporte_id': reporte.id_reporte,
            'progress': 5, 
            'status': 'STARTED'
        }
        return render(request, 'finance/reconciliacion/partials/task_progress.html', context)

    except Exception as e:
        logger.exception("Falla crítica en subida de conciliación:")
        return HttpResponse(f'<p class="text-status-danger text-xs font-bold">Error crítico: {str(e)}</p>')

def reconciliation_task_status_htmx(request, task_id):
    """
    Pilar 2: Controlador de Polling HTMX.
    Consulta Celery y devuelve el fragmento o redirige al terminar.
    """
    res = AsyncResult(task_id)
    
    # 1. Lógica de Redirección Automática al éxito (Superpoder HTMX)
    if res.status == 'SUCCESS':
        # El resultado de la tarea es el ID del reporte generado
        reporte_id = res.result
        response = HttpResponse()
        # Redirigimos al detalle para ver los resultados finales
        response['HX-Redirect'] = reverse('finance:reconciliacion_detail', kwargs={'pk': reporte_id})
        return response

    if res.status == 'FAILURE':
        return render(request, 'finance/reconciliacion/partials/task_progress.html', {
            'status': 'FAILURE',
            'error': str(res.result),
            'task_id': task_id
        })

    # 2. Polling Activo: Devolver progreso actual
    progress = 0
    if res.info and isinstance(res.info, dict):
        progress = res.info.get('progress', 0)

    return render(request, 'finance/reconciliacion/partials/task_progress.html', {
        'task_id': task_id,
        'progress': progress or 40, # Placeholder si no hay update aún
        'status': res.status,
        'task_finished': False
    })

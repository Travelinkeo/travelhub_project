import logging
from django.shortcuts import get_object_or_404
from django.http import FileResponse, HttpResponseForbidden, HttpResponse
from django.contrib.auth.decorators import login_required
from apps.finance.models.reconciliacion import ReporteReconciliacion
from apps.finance.services.pdf_service import PDFService
from apps.finance.tasks_notifications import enviar_reporte_gerencia_task

logger = logging.getLogger(__name__)

@login_required
def download_reconciliation_report_view(request, pk):
    """
    Pilar 3: Endpoint de Descarga.
    Recupera la conciliación, genera el PDF y lo envía al navegador.
    """
    reporte = get_object_or_404(ReporteReconciliacion, pk=pk)
    
    # 1. Blindaje Multi-Tenant (Seguridad de Datos)
    if reporte.agencia != request.user.agencia:
        logger.warning(f"🚨 Intento de acceso no autorizado al reporte {pk} por el usuario {request.user.username}")
        return HttpResponseForbidden("No tienes permisos para acceder a este reporte.")

    try:
        # 2. Generar el PDF dinámicamente en memoria
        pdf_file = PDFService.generate_reconciliation_report(pk, request.user)
        
        # 3. Devolver como descarga binaria (FileResponse)
        filename = f"Reporte_Conciliacion_{reporte.proveedor}_{reporte.fecha_subida.strftime('%Y%m%d')}.pdf"
        
        return FileResponse(
            pdf_file, 
            as_attachment=True, 
            filename=filename, 
            content_type='application/pdf'
        )

    except Exception as e:
        logger.error(f"Error sirviendo el PDF {pk}: {e}")
        return HttpResponseForbidden(f"Error generando el reporte: {str(e)}")

@login_required
def send_reconciliation_report_email_htmx(request, pk):
    """
    Controlador HTMX: Lanza la tarea de envío a gerencia y devuelve un botón de éxito.
    """
    if request.method != 'POST':
        return HttpResponse("Método no permitido", status=405)

    reporte = get_object_or_404(ReporteReconciliacion, pk=pk)
    
    # 1. Seguridad Multi-Tenant
    if reporte.agencia != request.user.agencia:
        return HttpResponseForbidden("No autorizado")

    # 2. Orquestar envío asíncrono
    # Usamos el email del usuario actual como destino (o el de la agencia si estuviera en el modelo)
    email_destino = request.user.email
    
    enviar_reporte_gerencia_task.delay(
        reporte_id=str(reporte.id_reporte),
        user_id=request.user.id,
        email_destino=email_destino
    )

    # 3. Devolver Fragmento HTMX de Éxito Instantáneo
    return HttpResponse("""
        <button class="btn-primary h-8 px-4 text-[10px] flex items-center gap-2 bg-status-success border-status-success pointer-events-none opacity-80 shadow-inner" disabled>
            <span class="material-symbols-outlined text-[16px]">check_circle</span>
            Reporte Enviado ✅
        </button>
    """)

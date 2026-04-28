from rest_framework import views, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from celery.result import AsyncResult
from apps.finance.models.reconciliacion import ReporteReconciliacion
import logging

logger = logging.getLogger(__name__)

class ReconciliationTaskStatusAPIView(views.APIView):
    """
    ENDPOINT DE RASTREO (EL CAJERO):
    Permite al frontend (NextJS/React) consultar el progreso de una 
    conciliación masiva de forma eficiente y sin sobrecargar la DB.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, task_id, *args, **kwargs):
        """
        Consulta estado en Celery/Redis y lo cruza con el modelo de Django
        para dar una respuesta híbrida completa.
        """
        # 1. Consultar estado en Celery/Redis
        res = AsyncResult(task_id)
        
        # 2. Consultar el reporte en DB si existe el reporte_id (como meta o parámetro extra)
        # Por ahora enviamos el estado de Celery crudo
        response_data = {
            "task_id": task_id,
            "ready": res.ready(),
            "status": res.status, # PENDING, STARTED, SUCCESS, FAILURE, RETRY
        }

        # 3. En caso de éxito, podemos devolver un resumen rápido si lo hay
        if res.ready() and res.status == 'SUCCESS':
            response_data["result"] = res.result
        
        # 4. Enriquecimiento opcional (Si falla la tarea, intentamos ver el log de error en DB)
        # Todo: Implementar búsqueda de reporte por task_id si fuera necesario 
        # en LineaReporteReconciliacion.task_id o similar.
            
        return Response(response_data)

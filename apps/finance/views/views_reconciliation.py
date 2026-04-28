import logging
import os
from rest_framework import views, status, parsers
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError
from django.core.cache import cache

from apps.finance.models.reconciliacion import ReporteReconciliacion
from apps.finance.serializers import ReporteReconciliacionSerializer
from apps.finance.tasks_reconciliation import conciliar_reporte_batch_task  # Importamos la nueva tarea asíncrona

logger = logging.getLogger(__name__)

class ReporteReconciliacionAsyncUploadAPIView(views.APIView):
    """
    Vista Fase 3 (Escalabilidad): Recibe archivos masivos de proveedores (5,000+ líneas),
    los guarda físicamente y dispara una tarea de Celery sin bloquear al usuario.
    Retorna 202 ACCEPTED con el ID del reporte para polling.
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [parsers.MultiPartParser, parsers.FormParser]

    def post(self, request, *args, **kwargs):
        # 1. Validar Agencia (Multi-Tenancy Blindage)
        user = request.user
        if not hasattr(user, 'perfil') or not user.perfil.agencia_id:
             raise ValidationError({"error": "Su usuario no tiene una agencia asociada para realizar conciliaciones."})
        
        agencia_id = user.perfil.agencia_id
        
        # 2. Persistencia inicial del reporte (Estado: PENDIENTE)
        serializer = ReporteReconciliacionSerializer(data=request.data)
        if serializer.is_valid():
            # Inyectamos la agencia del usuario actual
            reporte = serializer.save(
                agencia_id=agencia_id,
                estado='PENDIENTE'
            )
            
            # 3. Disparar Celery (Proceso Batch en Segundo Plano)
            # Pasamos agencia_id explícitamente para el aislamiento de datos en el worker
            task = conciliar_reporte_batch_task.delay(
                reporte_id=str(reporte.id_reporte),
                agencia_id=agencia_id
            )
            
            # 4. Retorno Inmediato (202 ACCEPTED)
            # Esto evita el timeout de 15+ segundos por procesamiento largo
            return Response({
                "status": "batch_processing_started",
                "message": "Archivo recibido correctamente. El proceso de conciliación ha comenzado en segundo plano.",
                "reporte_id": str(reporte.id_reporte),
                "task_id": task.id,
                "workflow": f"Polling: /api/finance/reportes/{reporte.id_reporte}/status/"
            }, status=status.HTTP_202_ACCEPTED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

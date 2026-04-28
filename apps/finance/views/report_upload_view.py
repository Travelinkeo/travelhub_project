from rest_framework import views, status, parsers
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from core.utils.celery_utils import safe_delay
from apps.finance.tasks_reconciliation import conciliar_reporte_batch_task
from apps.finance.models.reconciliacion import ReporteReconciliacion
import logging

logger = logging.getLogger(__name__)

class ReporteProveedorUploadAPIView(views.APIView):
    """
    PUENTE AL MOTOR DE CONCILIACIÓN (FRENTE DE CAJA):
    Acepta reportes masivos de proveedores y los deriva al carril pesado ia_heavy.
    Diseñado para responder en < 1s mientras el trabajo sucio ocurre en el motor IA.
    """
    parser_classes = (parsers.MultiPartParser, parsers.FormParser)
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        archivo = request.FILES.get('archivo')
        proveedor = request.data.get('proveedor', 'GDS') # SABRE, KIU, AMADEUS, CTG
        
        if not archivo:
            return Response({"error": "No se recibió ningún archivo."}, status=status.HTTP_400_BAD_REQUEST)

        # 1. BLINDAJE MULTI-TENANT : Identificar la Agencia del Usuario
        user_agencia = request.user.agencias.filter(activo=True).first()
        if not user_agencia:
            return Response({"error": "Tu cuenta no está vinculada a ninguna agencia activa."}, status=status.HTTP_403_FORBIDDEN)
        
        agencia = user_agencia.agencia

        # 2. ALMACENAMIENTO SEGURO (Regla de la Mochila)
        # Guardamos el archivo físicamente en disco (o S3 en producción)
        # El modelo ReporteReconciliacion se encarga de la gestión del FileField
        try:
            reporte = ReporteReconciliacion.objects.create(
                agencia=agencia,
                archivo=archivo,
                proveedor=proveedor,
                estado='PENDIENTE'
            )
        except Exception as e:
            logger.error(f"Error guardando reporte de reconciliación: {e}")
            return Response({"error": "Error interno al guardar el archivo."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # 3. ASISTENCIA DE CARRIL (Offloading a ia_heavy)
        # Usamos safe_delay para garantizar la disponibilidad del API ante fallos de Redis
        task = safe_delay(conciliar_reporte_batch_task, reporte.id_reporte, agencia.id)

        if task:
            # Respuesta rápida tipo "Cajero": Entrega el ticket de reclamo y libera al usuario
            return Response({
                "message": f"Reporte de {proveedor} recibido. El motor de IA está conciliando tus ventas.",
                "reporte_id": str(reporte.id_reporte),
                "task_id": task.id, # El ID de Celery para el seguimiento por parte del Frontend
                "estado": "PROCESANDO",
                "queue": "ia_heavy"
            }, status=status.HTTP_202_ACCEPTED)
        else:
            # Plan B: Si Celery falla, el registro queda en la BD para procesamiento asíncrono posterior
            return Response({
                "message": "Reporte recibido, pero el motor de IA está saturado. Se procesará automáticamente en breve.",
                "reporte_id": str(reporte.id_reporte),
                "estado": "COLA_LLENA"
            }, status=status.HTTP_202_ACCEPTED)

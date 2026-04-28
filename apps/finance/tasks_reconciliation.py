import logging
from decimal import Decimal
from celery import shared_task
from django.db import transaction
from django.utils import timezone
from apps.finance.models.reconciliacion import (
    ReporteReconciliacion,
    LineaReporteReconciliacion,
    ConciliacionBoleto
)
from apps.bookings.models import BoletoImportado
from apps.finance.services.reconciliation_engine import SmartReconciliator
from apps.finance.services.smart_reconciliation_service import SmartReconciliationService

logger = logging.getLogger(__name__)

@shared_task(name="finance.tasks_reconciliation.conciliar_reporte_batch_task")
def conciliar_reporte_batch_task(reporte_id, agencia_id):
    """
    Tarea Batch para procesar reportes de proveedores a gran escala.
    Delega la lógica principal al SmartReconciliationService para consistencia.
    """
    logger.info(f"🚀 Iniciando tarea de conciliación para Reporte {reporte_id}")
    
    try:
        # El servicio ya maneja la transacción, estados y lógica de IA
        from apps.finance.services.smart_reconciliation_service import SmartReconciliationService
        SmartReconciliationService.procesar_reporte(reporte_id)
        
        logger.info(f"✅ Tarea finalizada con éxito para Reporte {reporte_id}")
        return str(reporte_id)

    except Exception as e:
        logger.exception(f"❌ Error crítico en tarea de conciliación {reporte_id}: {str(e)}")
        return None

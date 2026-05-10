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
    Establece el contexto de agencia para asegurar el aislamiento de datos (SaaS).
    """
    from core.middleware import agency_context
    from core.models.agencia import Agencia
    
    logger.info(f"🚀 Iniciando tarea de conciliación para Reporte {reporte_id} (Agencia: {agencia_id})")
    
    try:
        # Recuperamos la agencia usando all_objects porque aún no tenemos contexto
        agencia = Agencia.all_objects.get(pk=agencia_id)
        
        with agency_context(agencia):
            # Ahora todas las queries dentro de este bloque estarán filtradas por esta agencia
            from apps.finance.services.smart_reconciliation_service import SmartReconciliationService
            SmartReconciliationService.procesar_reporte(reporte_id)
        
        logger.info(f"✅ Tarea finalizada con éxito para Reporte {reporte_id}")
        return str(reporte_id)

    except Exception as e:
        logger.exception(f"❌ Error crítico en tarea de conciliación {reporte_id}: {str(e)}")
        return None

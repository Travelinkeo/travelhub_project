"""Módulo tasks reconciliation de la aplicación finance.
"""

import logging

from celery import shared_task

from apps.common.utils.celery_utils import idempotent_task

logger = logging.getLogger(__name__)


@shared_task(
    name="finance.tasks_reconciliation.conciliar_reporte_batch_task",
    time_limit=600,
    soft_time_limit=540,
)
@idempotent_task(timeout=7200, key_prefix="celery_conciliar")
def conciliar_reporte_batch_task(reporte_id, agencia_id):
    """
    Tarea Batch para procesar reportes de proveedores a gran escala.
    Establece el contexto de agencia para asegurar el aislamiento de datos (SaaS).
    """
    from core.api import Agencia, agency_context

    logger.info(
        f"🚀 Iniciando tarea de conciliación para Reporte {reporte_id} (Agencia: {agencia_id})"
    )

    try:
        # Recuperamos la agencia usando all_objects porque aún no tenemos contexto
        agencia = Agencia.all_objects.get(pk=agencia_id)

        with agency_context(agencia):
            # Ahora todas las queries dentro de este bloque estarán filtradas por esta agencia
            from apps.finance.services.smart_reconciliation_service import (
                SmartReconciliationService,
            )

            SmartReconciliationService.procesar_reporte(reporte_id)

        logger.info(f"✅ Tarea finalizada con éxito para Reporte {reporte_id}")
        return str(reporte_id)

    except Exception as e:
        logger.exception(f"❌ Error crítico en tarea de conciliación {reporte_id}: {str(e)}")
        return None

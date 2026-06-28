import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(queue="ia_fast", max_retries=2, time_limit=60, soft_time_limit=50)
def evaluar_tax_refund_task(boleto_id, agencia_id=None):
    from apps.finance.services.tax_eligibility import TaxRefundEngine
    from core.api import Agencia, agency_context, system_context

    try:
        if agencia_id:
            agencia = Agencia.objects.get(pk=agencia_id)
            ctx = agency_context(agencia)
        else:
            ctx = system_context()

        with ctx:
            return TaxRefundEngine.evaluar_boleto(boleto_id)
    except Exception as e:
        logger.error(f"Error en evaluar_tax_refund_task para boleto {boleto_id}: {e}")
        return None

from celery import shared_task
import logging
from apps.finance.services.tax_eligibility import TaxRefundEngine

logger = logging.getLogger(__name__)

@shared_task(queue='ia_fast', max_retries=2)
def evaluar_tax_refund_task(boleto_id):
    """
    Tarea silenciosa que escanea el boleto justo después de parsearse.
    """
    try:
        return TaxRefundEngine.evaluar_boleto(boleto_id)
    except Exception as e:
        logger.error(f"Error en evaluar_tax_refund_task para boleto {boleto_id}: {e}")
        return None

import logging

from celery import shared_task
from django.utils import timezone

from apps.crm.models import ComisionFreelancer
from apps.crm.services.freelancer_service import FreelancerService

logger = logging.getLogger(__name__)


@shared_task
def liquidar_comisiones_mensual_task() -> str:
    """
    Tarea mensual (o manual) para liquidar todas las comisiones pendientes
    de freelancers activos y actualizar sus balances.
    """
    logger.info("Iniciando tarea de liquidación mensual de comisiones...")
    now = timezone.now()

    # Obtener todas las comisiones no liquidadas de freelancers activos
    comisiones_pendientes = ComisionFreelancer.objects.filter(
        liquidada=False, freelancer__activo=True, is_deleted=False
    ).select_related("freelancer")

    count = comisiones_pendientes.count()
    if count == 0:
        logger.info("No se encontraron comisiones pendientes de liquidar.")
        return "No comisiones to liquidate"

    # Agrupar freelancers afectados para actualizar sus balances al final
    freelancers_afectados = set()

    for comision in comisiones_pendientes:
        comision.liquidada = True
        comision.fecha_liquidacion = now
        comision.save(update_fields=["liquidada", "fecha_liquidacion"])
        freelancers_afectados.add(comision.freelancer)
        logger.info(f"Comisión {comision.pk} liquidada para freelancer {comision.freelancer.pk}")

    # Actualizar balances para cada freelancer afectado
    for freelancer in freelancers_afectados:
        FreelancerService.recalculate_balances(freelancer)

    msg = f"Liquidación completada exitosamente. Total comisiones liquidadas: {count}"
    logger.info(msg)
    return msg

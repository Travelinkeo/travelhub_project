# apps/finance/receivers.py
import logging

from django.dispatch import receiver

from core.api import sale_recalculation_requested

from .services.finance_service import FinanceService

logger = logging.getLogger(__name__)


@receiver(sale_recalculation_requested)
def handle_sale_recalculation(sender, **kwargs):
    """
    Escucha el evento 'sale_recalculation_requested' y ejecuta la lógica
    de recálculo financiero correspondiente.
    """
    venta_id = kwargs.get("venta_id")
    agencia_id = kwargs.get("agencia_id")  # Recibimos el agencia_id para futuro uso y consistencia.

    if not venta_id:
        logger.warning("Receiver 'handle_sale_recalculation' recibió una señal sin 'venta_id'.")
        return

    logger.info(
        f"🎧 Evento 'sale_recalculation_requested' recibido para Venta {venta_id}. Ejecutando FinanceService..."
    )

    try:
        # La lógica de negocio real sigue encapsulada en el servicio.
        # El receiver solo actúa como un punto de entrada desacoplado.
        FinanceService.recalculate_sale_finances(venta_id)
    except Exception as e:
        logger.error(
            f"Error en el receiver 'handle_sale_recalculation' para Venta {venta_id}: {e}",
            exc_info=True,
        )


from apps.finance.services.factura_contabilidad import generar_asiento_pago
from core.api import are_signals_blocked, sale_payment_recorded


@receiver(sale_payment_recorded)
def handle_sale_payment_accounting(sender, pago_id, estado_accion, agencia_id, **kwargs):
    """
    Escucha la señal 'sale_payment_recorded' y genera el asiento contable del pago
    de forma desacoplada y asilada del flujo principal.
    """
    if are_signals_blocked():
        return

    from apps.bookings.models import PagoVenta

    try:
        instance = PagoVenta.objects.filter(pk=pago_id).first()
        if not instance:
            logger.warning(
                f"handle_sale_payment_accounting: PagoVenta con id={pago_id} no encontrado."
            )
            return

        if estado_accion == "delete":
            instance.confirmado = False

        generar_asiento_pago(instance)
        logger.info(
            f"✅ Asiento contable de pago generado/actualizado para Pago {pago_id} (Acción: {estado_accion})"
        )
    except Exception as e:
        logger.error(f"Error procesando asiento contable para Pago {pago_id}: {e}")

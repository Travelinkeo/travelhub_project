# contabilidad/signals.py
"""
Señales para integración automática Facturación -> Contabilidad.
Se disparan al guardar facturas y pagos para generar asientos contables.
"""

import logging
from functools import partial

from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.bookings.models import PagoVenta
from apps.finance.models import Factura
from core.api import are_signals_blocked

from .services import ContabilidadService

logger = logging.getLogger(__name__)


def _on_commit(fn, *args, **kwargs):
    transaction.on_commit(partial(fn, *args, **kwargs))


@receiver(post_save, sender=Factura)
def generar_asiento_desde_factura_signal(sender, instance, created, **kwargs):
    """
    Genera asiento contable automáticamente al crear/actualizar una factura.
    Solo se ejecuta si la factura tiene items y está en estado válido.
    """
    if are_signals_blocked():
        logger.info(
            f"⏭️ SIGNAL: Signals blocked. Bypassing generar_asiento_desde_factura_signal for Factura {instance.pk}"
        )
        return

    if not created:
        return

    try:
        if not instance.items_factura.exists():
            logger.debug(f"Factura {instance.numero_factura} sin items, omitiendo asiento")
            return
    except Exception:
        return

    _on_commit(_generar_asiento_contable, instance.pk)


def _generar_asiento_contable(factura_id):
    from apps.finance.models import Factura as FacturaModel

    try:
        factura = FacturaModel.objects.get(pk=factura_id)
        asiento = ContabilidadService.generar_asiento_desde_factura(factura)
        logger.info(
            f"Asiento {asiento.numero_asiento} generado para factura {factura.numero_factura}"
        )
    except Exception as e:
        logger.error(f"Error generando asiento para factura {factura_id}: {e}")


@receiver(post_save, sender=PagoVenta)
def registrar_pago_y_diferencial_signal(sender, instance, created, **kwargs):
    """
    Registra el pago y calcula diferencial cambiario automáticamente.
    Solo se ejecuta para pagos confirmados.
    """
    if are_signals_blocked():
        logger.info(
            f"⏭️ SIGNAL: Signals blocked. Bypassing registrar_pago_y_diferencial_signal for PagoVenta {instance.pk}"
        )
        return

    if not instance.confirmado:
        return

    _on_commit(_registrar_pago_contable, instance.pk)


def _registrar_pago_contable(pago_id):
    from apps.bookings.models import PagoVenta as PagoVentaModel

    try:
        pago = PagoVentaModel.objects.get(pk=pago_id)
        asiento = ContabilidadService.registrar_pago_y_diferencial(pago)
        if asiento:
            logger.info(f"Asiento de pago {asiento.numero_asiento} generado para pago {pago_id}")
    except Exception as e:
        logger.error(f"Error registrando pago {pago_id}: {e}")

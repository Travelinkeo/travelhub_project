# apps/finance/signals.py
import logging
from functools import partial

from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.finance.services.factura_contabilidad import generar_asiento_factura
from core.api import ticket_invoicing_requested

from .models.core_finance import Factura
from .models.recaudacion import Pago
from .tasks import enviar_alerta_pago_telegram_task

logger = logging.getLogger(__name__)


def _on_commit(fn, *args, **kwargs):
    transaction.on_commit(partial(fn, *args, **kwargs))


@receiver(post_save, sender=Pago)
def disparar_alerta_recaudacion(sender, instance, created, **kwargs):
    """
    Detecta si un pago requiere aprobación manual (confirmado=False)
    y delega la alerta asíncronamente a Celery.
    """
    if created and not instance.confirmado:
        _on_commit(
            enviar_alerta_pago_telegram_task.delay, instance.id_pago, agencia_id=instance.agencia_id
        )


@receiver(post_save, sender=Factura)
def disparar_asiento_contable_factura(sender, instance, created, **kwargs):
    """
    Genera automáticamente el asiento contable en estado BORRADOR
    cuando la factura se emite (estado EMI, PAG, o PAR)
    y aún no tiene un asiento contable asignado.
    """
    if instance.estado in [
        Factura.EstadoFactura.EMITIDA,
        Factura.EstadoFactura.PAGADA,
        Factura.EstadoFactura.PARCIAL,
    ]:
        if not getattr(instance, "_contabilizando", False):
            factura_id = instance.pk
            _on_commit(_generar_asiento_factura_sync, factura_id)


def _generar_asiento_factura_sync(factura_id):
    from apps.finance.models.core_finance import Factura as FacturaModel

    try:
        instance = FacturaModel.objects.get(pk=factura_id)
        instance._contabilizando = True
        generar_asiento_factura(instance)
        logger.info(f"Asiento contable automático para Factura: {instance.numero_factura}")
    except Exception as e:
        logger.error(f"No se pudo generar asiento para factura {factura_id}: {e}")
    finally:
        try:
            instance._contabilizando = False
        except Exception:
            pass


@receiver(ticket_invoicing_requested)
def procesar_facturacion_automatica_boleto(
    sender, venta_id, formato_detectado, agencia_id, **kwargs
):
    """
    Escucha la solicitud de facturación de boletos y delega a Celery
    para evitar HTTP síncrono (BCV API) en el ciclo de request.
    """
    logger.info(
        f"📩 Evento 'ticket_invoicing_requested' recibido para Venta {venta_id} (Formato: {formato_detectado})"
    )
    from .tasks import create_invoice_from_sale_task

    _on_commit(create_invoice_from_sale_task.delay, venta_id)

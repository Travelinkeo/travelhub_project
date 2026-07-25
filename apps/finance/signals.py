"""Señales Django para la aplicación finance.
"""

import logging
from functools import partial

from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.finance.services.factura_contabilidad import generar_asiento_factura
from core.api import ticket_invoicing_requested

from .models import Factura, Pago

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Pago)
def disparar_alerta_recaudacion(sender, instance, created, **kwargs):
    # disparar_alerta_recaudacion: Disparar alerta recaudacion. Args: según implementación. Returns: según implementación.
    if created:
        transaction.on_commit(
            partial(
                lambda p: logger.info("Pago registrado: %s", p.pk),
                instance,
            )
        )


@receiver(post_save, sender=Factura)
def disparar_asiento_contable_factura(sender, instance, created, **kwargs):
    # disparar_asiento_contable_factura: Disparar asiento contable factura. Args: según implementación. Returns: según implementación.
    if instance.estado == Factura.EstadoFactura.EMITIDA:
        if not getattr(instance, "_contabilizando", False):
            factura_id = instance.pk
            transaction.on_commit(_generar_asiento_factura_sync, factura_id)


def _generar_asiento_factura_sync(factura_id):
    # _generar_asiento_factura_sync:  generar asiento factura sync. Args: según implementación. Returns: según implementación.
    try:
        instance = Factura.objects.get(pk=factura_id)
        instance._contabilizando = True
        generar_asiento_factura(instance)
        logger.info(f"Asiento contable automático para Factura: {instance.numero_control}")
    except Exception as e:
        logger.error(f"No se pudo generar asiento para factura {factura_id}: {e}")
    finally:
        try:
            instance._contabilizando = False
        except Exception as e:
            logger.debug("Error restaurando flag _contabilizando: %s", e)


@receiver(ticket_invoicing_requested)
def procesar_facturacion_automatica_boleto(
    sender, venta_id, formato_detectado, agencia_id, **kwargs
):
    # procesar_facturacion_automatica_boleto: Procesa r facturacion automatica boleto. Args: datos a procesar. Returns: resultado procesado.
    logger.info(
        f"Evento ticket_invoicing_requested para Venta {venta_id} (Formato: {formato_detectado})"
    )
    from .tasks import create_invoice_from_sale_task

    transaction.on_commit(create_invoice_from_sale_task.delay, venta_id)

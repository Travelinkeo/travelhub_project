import logging
from functools import partial

from django.db import transaction
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from core.api import are_signals_blocked

# 🔒 PADLOCK: CRITICAL INFRASTRUCTURE
# Refactored to Service Layer Pattern. Signals are now thin wrappers
# delegating to explicit service classes, supporting thread-local bypassing.
# Maintained by: Antigravity/Gemini
# -----------------------------------------------------
from .models import BoletoImportado, CircuitoDia, FeeVenta, ItemVenta, PagoVenta, Venta

logger = logging.getLogger(__name__)


def _on_commit(fn, *args, **kwargs):
    transaction.on_commit(partial(fn, *args, **kwargs))


@receiver([post_save, post_delete], sender=FeeVenta)
def signal_fee_post_save_delete(sender, instance, **kwargs):
    if are_signals_blocked():
        logger.info(
            f"⏭️ SIGNAL: Signals blocked. Bypassing signal_fee_post_save_delete for FeeVenta {instance.pk}"
        )
        return

    if instance.venta_id:
        _on_commit(_recalcular_sync, instance.venta_id)


def _recalcular_sync(venta_id):
    from apps.bookings.services.venta_service import VentaService

    VentaService.recalculate_finances(venta_id)


@receiver([post_save, post_delete], sender=ItemVenta)
def signal_item_post_save_delete(sender, instance, **kwargs):
    if are_signals_blocked():
        logger.info(
            f"⏭️ SIGNAL: Signals blocked. Bypassing signal_item_post_save_delete for ItemVenta {instance.pk}"
        )
        return

    if instance.venta_id:
        _on_commit(_recalcular_sync, instance.venta_id)
        _on_commit(_auditar_venta_sync, instance.venta_id)


@receiver(post_save, sender=BoletoImportado)
def signal_boleto_post_save(sender, instance, created, **kwargs):
    if are_signals_blocked():
        logger.info(
            f"⏭️ SIGNAL: Signals blocked. Bypassing signal_boleto_post_save for Boleto {instance.pk}"
        )
        return

    _on_commit(_evaluar_tax_refund, instance.pk)
    if created:
        _on_commit(_notificar_boleto_importado, instance.pk)


@receiver(post_save, sender=PagoVenta)
def signal_pago_post_save(sender, instance, created, **kwargs):
    if are_signals_blocked():
        logger.info(
            f"⏭️ SIGNAL: Signals blocked. Bypassing signal_pago_post_save for PagoVenta {instance.pk}"
        )
        return

    if instance.venta_id:
        pago_id, agencia_id = instance.pk, instance.agencia_id
        _on_commit(_recalcular_sync, instance.venta_id)
        _on_commit(_evaluar_loyalty_sync, instance.pk)
        _on_commit(_emitir_pago_evento, pago_id, "save", agencia_id)
        if created:
            _on_commit(_notificar_pago_confirmado, instance.pk)


@receiver(post_delete, sender=PagoVenta)
def signal_pago_post_delete(sender, instance, **kwargs):
    if are_signals_blocked():
        logger.info(
            f"⏭️ SIGNAL: Signals blocked. Bypassing signal_pago_post_delete for PagoVenta {instance.pk}"
        )
        return

    if instance.venta_id:
        _on_commit(_recalcular_sync, instance.venta_id)
        _on_commit(_evaluar_loyalty_sync, instance.pk)
        _on_commit(_emitir_pago_evento, instance.pk, "delete", instance.agencia_id)


@receiver(pre_save, sender=Venta)
def capturar_estado_anterior_venta(sender, instance, **kwargs):
    if are_signals_blocked():
        logger.info(
            f"⏭️ SIGNAL: Signals blocked. Bypassing capturar_estado_anterior_venta for Venta {instance.pk}"
        )
        return

    if instance.pk:
        try:
            obj_db = Venta.all_objects.get(pk=instance.pk)
            instance._estado_anterior = obj_db.estado
        except Venta.DoesNotExist:
            instance._estado_anterior = None
    else:
        instance._estado_anterior = None


@receiver(post_save, sender=Venta)
def venta_post_save_dispatcher(sender, instance, created, **kwargs):
    if are_signals_blocked():
        logger.info(
            f"⏭️ SIGNAL: Signals blocked. Bypassing venta_post_save_dispatcher for Venta {instance.pk}"
        )
        return

    if kwargs.get("raw", False):
        return

    estado_anterior = getattr(instance, "_estado_anterior", None)

    _on_commit(_disparar_post_save_actions, instance.pk, created, estado_anterior)
    _on_commit(_auditar_venta_sync, instance.pk)


@receiver([post_save, post_delete], sender=CircuitoDia)
def actualizar_circuito_dias(sender, instance, **kwargs):
    if are_signals_blocked():
        logger.info(
            f"⏭️ SIGNAL: Signals blocked. Bypassing actualizar_circuito_dias for CircuitoDia {instance.pk}"
        )
        return

    _on_commit(_update_circuit_days_sync, instance.pk)


# ── Helper functions for on_commit callbacks ──────────────


def _auditar_venta_sync(venta_id):
    from apps.bookings.services.revenue_auditor import RevenueAuditorService

    try:
        from apps.bookings.models import Venta

        venta = Venta.objects.get(pk=venta_id)
        RevenueAuditorService().audit_venta(venta)
    except Exception as e:
        logger.error(f"Error auditando venta {venta_id}: {e}")


def _evaluar_tax_refund(boleto_id):
    from apps.bookings.models import BoletoImportado
    from apps.bookings.services.boleto_service import BoletoImportadoService

    try:
        # Usar all_objects para funcionar fuera del contexto de agencia (on_commit callback)
        manager = getattr(BoletoImportado, "all_objects", BoletoImportado.objects)
        boleto = manager.get(pk=boleto_id)
        BoletoImportadoService.evaluate_tax_refund(boleto)
    except Exception as e:
        logger.error(f"Error evaluando tax refund para boleto {boleto_id}: {e}")


def _evaluar_loyalty_sync(pago_id):
    from apps.bookings.models import PagoVenta
    from apps.bookings.services.venta_service import VentaService

    try:
        pago = PagoVenta.objects.get(pk=pago_id)
        VentaService.evaluate_loyalty_points(pago)
    except Exception as e:
        logger.error(f"Error evaluando loyalty para pago {pago_id}: {e}")


def _emitir_pago_evento(pago_id, estado_accion, agencia_id):
    try:
        from apps.bookings.models import PagoVenta
        from core.api import sale_payment_recorded

        sale_payment_recorded.send(
            sender=PagoVenta,
            pago_id=pago_id,
            estado_accion=estado_accion,
            agencia_id=agencia_id,
        )
    except Exception as e:
        logger.error(
            f"Error emitiendo sale_payment_recorded ({estado_accion}) para pago {pago_id}: {e}"
        )


def _disparar_post_save_actions(venta_id, created, estado_anterior):
    from apps.bookings.models import Venta
    from apps.bookings.services.venta_service import VentaService

    try:
        venta = Venta.objects.get(pk=venta_id)
        VentaService.dispatch_post_save_actions(venta, created, estado_anterior)
        if created:
            from core.api.webhook_dispatcher import notify_venta_creada

            notify_venta_creada(venta)
    except Venta.DoesNotExist:
        logger.warning(f"Venta {venta_id} no existe para dispatch_post_save_actions")


def _update_circuit_days_sync(circuito_dia_id):
    from apps.bookings.models import CircuitoDia
    from apps.bookings.services.venta_service import VentaService

    try:
        cd = CircuitoDia.objects.get(pk=circuito_dia_id)
        VentaService.update_circuit_days(cd)
    except Exception as e:
        logger.error(f"Error actualizando circuit days: {e}")


def _notificar_pago_confirmado(pago_id):
    from apps.bookings.models import PagoVenta

    try:
        pago = PagoVenta.objects.get(pk=pago_id)
        from core.api.webhook_dispatcher import notify_pago_confirmado

        notify_pago_confirmado(pago)
    except PagoVenta.DoesNotExist:
        logger.warning(f"PagoVenta {pago_id} no existe para webhook")


def _notificar_boleto_importado(boleto_id):
    from apps.bookings.models import BoletoImportado

    try:
        boleto = BoletoImportado.objects.get(pk=boleto_id)
        from core.api.webhook_dispatcher import notify_boleto_importado

        notify_boleto_importado(boleto)
    except BoletoImportado.DoesNotExist:
        logger.warning(f"BoletoImportado {boleto_id} no existe para webhook")

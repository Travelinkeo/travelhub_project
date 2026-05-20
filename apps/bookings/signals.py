import logging
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver
from core.signals_bypass import are_signals_blocked

# 🔒 PADLOCK: CRITICAL INFRASTRUCTURE
# Refactored to Service Layer Pattern. Signals are now thin wrappers
# delegating to explicit service classes, supporting thread-local bypassing.
# Maintained by: Antigravity/Gemini
# -----------------------------------------------------

logger = logging.getLogger(__name__)

# Import models dynamically or directly
from .models import BoletoImportado, CircuitoDia, FeeVenta, ItemVenta, PagoVenta, Venta

@receiver([post_save, post_delete], sender=FeeVenta)
def signal_fee_post_save_delete(sender, instance, **kwargs):
    if are_signals_blocked():
        logger.info(f"⏭️ SIGNAL: Signals blocked. Bypassing signal_fee_post_save_delete for FeeVenta {instance.pk}")
        return

    if instance.venta_id:
        from apps.bookings.services.venta_service import VentaService
        VentaService.recalculate_finances(instance.venta_id)


@receiver([post_save, post_delete], sender=ItemVenta)
def signal_item_post_save_delete(sender, instance, **kwargs):
    if are_signals_blocked():
        logger.info(f"⏭️ SIGNAL: Signals blocked. Bypassing signal_item_post_save_delete for ItemVenta {instance.pk}")
        return

    if instance.venta_id:
        from apps.bookings.services.venta_service import VentaService
        VentaService.recalculate_finances(instance.venta_id)


@receiver(post_save, sender=BoletoImportado)
def signal_boleto_post_save(sender, instance, created, **kwargs):
    if are_signals_blocked():
        logger.info(f"⏭️ SIGNAL: Signals blocked. Bypassing signal_boleto_post_save for Boleto {instance.pk}")
        return

    # --- Delegate to Service Layer ---
    from apps.bookings.services.boleto_service import BoletoImportadoService
    BoletoImportadoService.evaluate_tax_refund(instance)


@receiver(post_save, sender=PagoVenta)
def signal_pago_post_save(sender, instance, created, **kwargs):
    if are_signals_blocked():
        logger.info(f"⏭️ SIGNAL: Signals blocked. Bypassing signal_pago_post_save for PagoVenta {instance.pk}")
        return

    if instance.venta_id:
        from apps.bookings.services.venta_service import VentaService
        VentaService.recalculate_finances(instance.venta_id)
        
        # Award loyalty points if Venta is present
        VentaService.evaluate_loyalty_points(instance)


@receiver(post_delete, sender=PagoVenta)
def signal_pago_post_delete(sender, instance, **kwargs):
    if are_signals_blocked():
        logger.info(f"⏭️ SIGNAL: Signals blocked. Bypassing signal_pago_post_delete for PagoVenta {instance.pk}")
        return

    try:
        if instance.venta_id:
            from apps.bookings.services.venta_service import VentaService
            VentaService.recalculate_finances(instance.venta_id)
            VentaService.evaluate_loyalty_points(instance)
    except Exception as e:
        logger.warning(f"Excepción silenciosa capturada en signal_pago_post_delete: {e}")


@receiver(pre_save, sender=Venta)
def capturar_estado_anterior_venta(sender, instance, **kwargs):
    if are_signals_blocked():
        logger.info(f"⏭️ SIGNAL: Signals blocked. Bypassing capturar_estado_anterior_venta for Venta {instance.pk}")
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
        logger.info(f"⏭️ SIGNAL: Signals blocked. Bypassing venta_post_save_dispatcher for Venta {instance.pk}")
        return

    if kwargs.get('raw', False):
        return

    estado_anterior = getattr(instance, '_estado_anterior', None)
    
    # --- Delegate to Service Layer ---
    from apps.bookings.services.venta_service import VentaService
    VentaService.dispatch_post_save_actions(instance, created, estado_anterior)


@receiver([post_save, post_delete], sender=CircuitoDia)
def actualizar_circuito_dias(sender, instance, **kwargs):
    if are_signals_blocked():
        logger.info(f"⏭️ SIGNAL: Signals blocked. Bypassing actualizar_circuito_dias for CircuitoDia {instance.pk}")
        return

    # --- Delegate to Service Layer ---
    from apps.bookings.services.venta_service import VentaService
    VentaService.update_circuit_days(instance)

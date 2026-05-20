import logging
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from core.signals_bypass import are_signals_blocked

# 🔒 PADLOCK: CRITICAL INFRASTRUCTURE
# Refactored to Service Layer Pattern. Signals are now thin wrappers
# delegating to explicit service classes, supporting thread-local bypassing.
# Maintained by: Antigravity/Gemini
# -----------------------------------------------------

logger = logging.getLogger(__name__)

@receiver(post_save, sender='bookings.BoletoImportado')
def crear_o_actualizar_venta_desde_boleto(sender, instance, created, **kwargs):
    if are_signals_blocked():
        logger.info(f"⏭️ SIGNAL: Signals blocked. Bypassing crear_o_actualizar_venta_desde_boleto for Boleto {instance.pk}")
        return

    # Evitar recursión si solo estamos actualizando la venta_asociada
    update_fields = kwargs.get('update_fields') or set()
    if 'venta_asociada' in update_fields and len(update_fields) == 1:
        return

    # Permitir bypass explícito de la señal
    if getattr(instance, '_skip_auto_parse', False):
        logger.info(f"⏭️ SIGNAL: Bypass activado para Boleto {instance.pk}. No se disparará la cola por defecto.")
        return

    # --- Delegate to Service Layer ---
    from apps.bookings.services.boleto_service import BoletoImportadoService
    BoletoImportadoService.trigger_parsing_if_needed(instance)


@receiver(post_save, sender='bookings.BoletoImportado')
def post_save_boleto_importado(sender, instance, created, **kwargs):
    if are_signals_blocked():
        logger.info(f"⏭️ SIGNAL: Signals blocked. Bypassing post_save_boleto_importado for Boleto {instance.pk}")
        return

    # --- Delegate to Service Layer ---
    from apps.bookings.services.boleto_service import BoletoImportadoService
    BoletoImportadoService.post_parse_automation(instance)


@receiver(post_save, sender='bookings.PagoVenta')
def enviar_confirmacion_pago_recibido(sender, instance, created, **kwargs):
    if are_signals_blocked():
        logger.info(f"⏭️ SIGNAL: Signals blocked. Bypassing enviar_confirmacion_pago_recibido for PagoVenta {instance.pk}")
        return

    if kwargs.get('raw', False):
        return
    
    if created and instance.confirmado:
        try:
            from apps.communications.services.notification_dispatcher import notificar_confirmacion_pago
            notificar_confirmacion_pago(instance)
        except Exception as e:
            logger.error(f"Error notifying payment confirmation: {e}")


@receiver(post_save, sender='core.MigrationCheck')
def enviar_alerta_migratoria(sender, instance, created, **kwargs):
    if are_signals_blocked():
        logger.info(f"⏭️ SIGNAL: Signals blocked. Bypassing enviar_alerta_migratoria for MigrationCheck {instance.pk}")
        return

    if kwargs.get('raw', False):
        return

    # --- Delegate to Service Layer ---
    from apps.crm.services.migration_service import MigrationService
    MigrationService.trigger_migration_alert_if_needed(instance, created)


@receiver(pre_save, sender='finance.Factura')
def capturar_pdf_factura_anterior(sender, instance, **kwargs):
    if are_signals_blocked():
        logger.info(f"⏭️ SIGNAL: Signals blocked. Bypassing capturar_pdf_factura_anterior for Factura {instance.pk}")
        return

    # --- Delegate to Service Layer ---
    from apps.finance.services.factura_service import FacturaService
    FacturaService.capture_previous_pdf(instance)


@receiver(post_save, sender='finance.Factura')
def post_save_factura(sender, instance, created, **kwargs):
    if are_signals_blocked():
        logger.info(f"⏭️ SIGNAL: Signals blocked. Bypassing post_save_factura for Factura {instance.pk}")
        return

    if kwargs.get('raw', False):
        return

    # --- Delegate to Service Layer ---
    from apps.finance.services.factura_service import FacturaService
    FacturaService.send_to_telegram_if_needed(instance)
    FacturaService.send_to_whatsapp_if_needed(instance)


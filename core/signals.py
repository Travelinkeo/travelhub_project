import logging
from functools import partial

from django.db import transaction
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from core.signals_bypass import are_signals_blocked


def _on_commit(fn, *args, **kwargs):
    transaction.on_commit(partial(fn, *args, **kwargs))

# 🔒 PADLOCK: CRITICAL INFRASTRUCTURE
# Refactored to Service Layer Pattern. Signals are now thin wrappers
# delegating to explicit service classes, supporting thread-local bypassing.
# Maintained by: Antigravity/Gemini
# -----------------------------------------------------

logger = logging.getLogger(__name__)


@receiver(post_save, sender="bookings.BoletoImportado")
def crear_o_actualizar_venta_desde_boleto(sender, instance, created, **kwargs):
    if are_signals_blocked():
        logger.info(
            f"⏭️ SIGNAL: Signals blocked. Bypassing crear_o_actualizar_venta_desde_boleto for Boleto {instance.pk}"
        )
        return

    # Evitar recursión si solo estamos actualizando la venta_asociada
    update_fields = kwargs.get("update_fields") or set()
    if "venta_asociada" in update_fields and len(update_fields) == 1:
        return

    # Permitir bypass explícito de la señal
    if getattr(instance, "_skip_auto_parse", False):
        logger.info(
            f"⏭️ SIGNAL: Bypass activado para Boleto {instance.pk}. No se disparará la cola por defecto."
        )
        return

    _on_commit(_trigger_parsing, instance.pk)


@receiver(post_save, sender="bookings.BoletoImportado")
def post_save_boleto_importado(sender, instance, created, **kwargs):
    if are_signals_blocked():
        logger.info(
            f"⏭️ SIGNAL: Signals blocked. Bypassing post_save_boleto_importado for Boleto {instance.pk}"
        )
        return

    _on_commit(_post_parse_automation, instance.pk)


@receiver(post_save, sender="bookings.PagoVenta")
def enviar_confirmacion_pago_recibido(sender, instance, created, **kwargs):
    if are_signals_blocked():
        logger.info(
            f"⏭️ SIGNAL: Signals blocked. Bypassing enviar_confirmacion_pago_recibido for PagoVenta {instance.pk}"
        )
        return

    if kwargs.get("raw", False):
        return

    if created and instance.confirmado:
        _on_commit(_notificar_pago, instance.pk)


@receiver(post_save, sender="core.MigrationCheck")
def enviar_alerta_migratoria(sender, instance, created, **kwargs):
    if are_signals_blocked():
        logger.info(
            f"⏭️ SIGNAL: Signals blocked. Bypassing enviar_alerta_migratoria for MigrationCheck {instance.pk}"
        )
        return

    if kwargs.get("raw", False):
        return

    _on_commit(_trigger_migration_alert, instance.pk, created)


@receiver(pre_save, sender="finance.Factura")
def capturar_pdf_factura_anterior(sender, instance, **kwargs):
    if are_signals_blocked():
        logger.info(
            f"⏭️ SIGNAL: Signals blocked. Bypassing capturar_pdf_factura_anterior for Factura {instance.pk}"
        )
        return

    _on_commit(_capturar_pdf_anterior, instance.pk)


@receiver(post_save, sender="finance.Factura")
def post_save_factura(sender, instance, created, **kwargs):
    if are_signals_blocked():
        logger.info(
            f"⏭️ SIGNAL: Signals blocked. Bypassing post_save_factura for Factura {instance.pk}"
        )
        return

    if kwargs.get("raw", False):
        return

    _on_commit(_send_factura_telegram, instance.pk)
    _on_commit(_send_factura_whatsapp, instance.pk)

# ── Helper functions for on_commit callbacks ──────────────


def _trigger_parsing(boleto_id):
    from apps.bookings.services.boleto_service import BoletoImportadoService
    from apps.bookings.models import BoletoImportado

    try:
        boleto = BoletoImportado.objects.get(pk=boleto_id)
        BoletoImportadoService.trigger_parsing_if_needed(boleto)
    except Exception as e:
        logger.error(f"Error triggering parsing for boleto {boleto_id}: {e}")


def _post_parse_automation(boleto_id):
    from apps.bookings.services.boleto_service import BoletoImportadoService
    from apps.bookings.models import BoletoImportado

    try:
        boleto = BoletoImportado.objects.get(pk=boleto_id)
        BoletoImportadoService.post_parse_automation(boleto)
    except Exception as e:
        logger.error(f"Error post-parse automation for boleto {boleto_id}: {e}")


def _notificar_pago(pago_id):
    from apps.communications.services.notification_dispatcher import notificar_confirmacion_pago
    from apps.bookings.models import PagoVenta

    try:
        pago = PagoVenta.objects.get(pk=pago_id)
        notificar_confirmacion_pago(pago)
    except Exception as e:
        logger.error(f"Error notificando pago {pago_id}: {e}")


def _trigger_migration_alert(check_id, created):
    from apps.crm.services.migration_service import MigrationService
    from core.models.migration_checks import MigrationCheck

    try:
        check = MigrationCheck.objects.get(pk=check_id)
        MigrationService.trigger_migration_alert_if_needed(check, created)
    except Exception as e:
        logger.error(f"Error triggering migration alert {check_id}: {e}")


def _capturar_pdf_anterior(factura_id):
    from apps.finance.services.factura_service import FacturaService
    from apps.finance.models.core_finance import Factura

    try:
        factura = Factura.objects.get(pk=factura_id)
        FacturaService.capture_previous_pdf(factura)
    except Exception as e:
        logger.error(f"Error capturing PDF for factura {factura_id}: {e}")


def _send_factura_telegram(factura_id):
    from apps.finance.services.factura_service import FacturaService
    from apps.finance.models.core_finance import Factura

    try:
        factura = Factura.objects.get(pk=factura_id)
        FacturaService.send_to_telegram_if_needed(factura)
    except Exception as e:
        logger.error(f"Error sending factura {factura_id} to Telegram: {e}")


def _send_factura_whatsapp(factura_id):
    from apps.finance.services.factura_service import FacturaService
    from apps.finance.models.core_finance import Factura

    try:
        factura = Factura.objects.get(pk=factura_id)
        FacturaService.send_to_whatsapp_if_needed(factura)
    except Exception as e:
        logger.error(f"Error sending factura {factura_id} to WhatsApp: {e}")

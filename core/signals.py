import logging
from functools import partial

from django.core.signals import request_finished
from django.db import transaction
from django.db.models.signals import post_save, pre_save
from django.dispatch import Signal, receiver

from core.middleware import (
    agency_var,
    impersonator_var,
    is_impersonating_var,
    meta_var,
    system_context_var,
    user_var,
)
from core.signals_bypass import are_signals_blocked


def _on_commit(fn, *args, **kwargs):
    """_on_commit."""
    transaction.on_commit(partial(fn, *args, **kwargs))


# 🔒 PADLOCK: CRITICAL INFRASTRUCTURE
# Refactored to Service Layer Pattern. Signals are now thin wrappers
# delegating to explicit service classes, supporting thread-local bypassing.
# Maintained by: Antigravity/Gemini
# -----------------------------------------------------

logger = logging.getLogger(__name__)


# Señal para procesar reportes de proveedor PDF recibidos por email.
# Emitida por el dominio communications, escuchada por contabilidad
# (evita la importación directa communications -> contabilidad).
reporte_proveedor_pdf_recibido = Signal()


@receiver(post_save, sender="bookings.BoletoImportado")
def on_boleto_importado_post_save(sender, instance, created, **kwargs):
    """
    Señal única consolidada (P1-001) para BoletoImportado.
    Orquesta tanto el trigger de parsing como el post-parse automation de manera segura.
    """
    if are_signals_blocked():
        logger.info(
            f"⏭️ SIGNAL: Signals blocked. Bypassing post-save automation for Boleto {instance.pk}"
        )
        return

    # Evitar recursión infinita cuando solo se asocia la venta al boleto
    update_fields = kwargs.get("update_fields") or set()
    if "venta_asociada" in update_fields and len(update_fields) == 1:
        return

    # Permitir bypass explícito de automatización
    if getattr(instance, "_skip_auto_parse", False):
        logger.info(
            f"⏭️ SIGNAL: Bypass activado para Boleto {instance.pk}. Omitiendo parsing y automatización."
        )
        return

    # Encolar ambas acciones seguras tras el commit de la transacción actual
    _on_commit(_trigger_parsing, instance.pk)
    _on_commit(_post_parse_automation, instance.pk)


@receiver(post_save, sender="bookings.PagoVenta")
def enviar_confirmacion_pago_recibido(sender, instance, created, **kwargs):
    """enviar_confirmacion_pago_recibido."""
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
    """enviar_alerta_migratoria."""
    if are_signals_blocked():
        logger.info(
            f"⏭️ SIGNAL: Signals blocked. Bypassing enviar_alerta_migratoria for MigrationCheck {instance.pk}"
        )
        return

    if kwargs.get("raw", False):
        return

    _on_commit(_trigger_migration_alert, instance.pk, created)


# 🔒 P1-004 FIX: Invalidación inmediata del cache de agencia al desactivar
@receiver(post_save, sender="core.Agencia")
def on_agencia_status_changed(sender, instance, **kwargs):
    """
    Cuando una Agencia se desactiva, invalida el cache de TODOS sus usuarios inmediatamente.
    Esto cierra la ventana de acceso no autorizado de hasta 120 segundos.
    """
    if kwargs.get("raw", False):
        return
    if not instance.activa:
        logger.warning(
            f"🚨 [SECURITY] Agencia '{instance.nombre}' (pk={instance.pk}) DESACTIVADA. "
            f"Invalidando cache de acceso para todos sus usuarios."
        )
        from core.security import invalidate_all_agency_caches

        invalidate_all_agency_caches(instance.pk)


@receiver(post_save, sender="core.UsuarioAgencia")
def on_usuario_agencia_changed(sender, instance, **kwargs):
    """Invalida el cache cuando cambia la relación usuario-agencia (activación, cambio de rol, etc.)."""
    if kwargs.get("raw", False):
        return
    from core.security import invalidate_user_agencia_cache

    invalidate_user_agencia_cache(instance.usuario_id)


@receiver(pre_save, sender="finance.Factura")
def capturar_pdf_factura_anterior(sender, instance, **kwargs):
    """capturar_pdf_factura_anterior."""
    if are_signals_blocked():
        return

    try:
        from apps.finance.models import Factura
        from apps.finance.services.factura_service import FacturaService

        if instance.pk:
            factura = Factura.objects.get(pk=instance.pk)
            FacturaService.capture_previous_pdf(factura)
    except Factura.DoesNotExist:
        pass
    except Exception as e:
        logger.error(f"Error capturing PDF for factura {instance.pk}: {e}")


@receiver(post_save, sender="finance.Factura")
def post_save_factura(sender, instance, created, **kwargs):
    """post_save_factura."""
    if are_signals_blocked():
        logger.info(
            f"⏭️ SIGNAL: Signals blocked. Bypassing post_save_factura for Factura {instance.pk}"
        )
        return

    if kwargs.get("raw", False):
        return

    _on_commit(_send_factura_telegram, instance.pk)
    _on_commit(_send_factura_whatsapp, instance.pk)


# ═══════════════════════════════════════════════════════════════════════════════
# 🛡️ REDUNDANCIA DE SEGURIDAD MULTI-TENANT (Defensa en Profundidad)
# ═══════════════════════════════════════════════════════════════════════════════
@receiver(request_finished)
def purgar_contextvars_de_seguridad(sender, **kwargs):
    """
    Última línea de defensa de TravelHub.
    Se dispara al nivel más bajo del framework justo antes de que Django envíe
    la respuesta al servidor WSGI/ASGI y cierre el request.

    Si ThreadLocalContextMiddleware falla por un OOM, un segfault en una librería C,
    o un Middleware superior interrumpe la cadena, este listener garantiza
    que el hilo (thread) quede esterilizado antes de ser reciclado por Gunicorn.
    """
    try:
        agency_var.set(None)
        user_var.set(None)
        meta_var.set(None)
        is_impersonating_var.set(False)
        impersonator_var.set(None)
        system_context_var.set(False)
    except Exception as e:
        logger.critical(f"FATAL: Error al purgar ContextVars en request_finished: {e}")


# ── Helper functions for on_commit callbacks ──────────────


def _trigger_parsing(boleto_id):
    """_trigger_parsing."""
    from apps.bookings.models import BoletoImportado
    from apps.bookings.services.boleto_service import BoletoImportadoService

    try:
        manager = getattr(BoletoImportado, "all_objects", BoletoImportado.objects)
        boleto = manager.get(pk=boleto_id)
        BoletoImportadoService.trigger_parsing_if_needed(boleto)
    except Exception as e:
        logger.error(f"Error triggering parsing for boleto {boleto_id}: {e}")


def _post_parse_automation(boleto_id):
    """_post_parse_automation."""
    from apps.bookings.models import BoletoImportado
    from apps.bookings.services.boleto_service import BoletoImportadoService

    try:
        manager = getattr(BoletoImportado, "all_objects", BoletoImportado.objects)
        boleto = manager.get(pk=boleto_id)
        BoletoImportadoService.post_parse_automation(boleto)
    except Exception as e:
        logger.error(f"Error post-parse automation for boleto {boleto_id}: {e}")


def _notificar_pago(pago_id):
    """_notificar_pago."""
    from apps.common.tasks import notificar_confirmacion_pago_task

    notificar_confirmacion_pago_task.delay(pago_id)


def _trigger_migration_alert(check_id, created):
    """_trigger_migration_alert."""
    if not created:
        return
    from apps.common.tasks import notify_migration_alert_task

    notify_migration_alert_task.delay(check_id)


def _capturar_pdf_anterior(factura_id):
    """_capturar_pdf_anterior."""
    from apps.finance.models import Factura
    from apps.finance.services.factura_service import FacturaService

    try:
        factura = Factura.objects.get(pk=factura_id)
        FacturaService.capture_previous_pdf(factura)
    except Exception as e:
        logger.error(f"Error capturing PDF for factura {factura_id}: {e}")


def _send_factura_telegram(factura_id):
    """_send_factura_telegram."""
    from apps.common.tasks import send_factura_to_telegram_task

    send_factura_to_telegram_task.delay(factura_id)


def _send_factura_whatsapp(factura_id):
    """_send_factura_whatsapp."""
    from apps.common.tasks import send_factura_to_whatsapp_task

    try:
        send_factura_to_whatsapp_task.delay(factura_id)
    except Exception as e:
        logger.error(f"Error encolando envío de factura {factura_id} a WhatsApp: {e}")

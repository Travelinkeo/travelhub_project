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
from core.signals import reporte_proveedor_pdf_recibido

from .services import ContabilidadService

logger = logging.getLogger(__name__)


def _on_commit(fn, *args, **kwargs):
    """_on_commit."""
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
        items_qs = getattr(instance, "items", None) or getattr(instance, "items_factura", None)
        if items_qs is not None and not items_qs.exists():
            num = getattr(
                instance, "numero_control", getattr(instance, "numero_factura", instance.pk)
            )
            logger.debug(f"Factura {num} sin items, omitiendo asiento")
            return
    except Exception:
        num = getattr(instance, "numero_control", getattr(instance, "numero_factura", instance.pk))
        logger.warning(
            "Error verificando items para factura %s",
            num,
            exc_info=True,
        )
        return

    _on_commit(_generar_asiento_contable, instance.pk)


def _generar_asiento_contable(factura_id):
    """_generar_asiento_contable."""
    from apps.finance.models import Factura as FacturaModel

    try:
        factura = FacturaModel.objects.get(pk=factura_id)
        asiento = ContabilidadService.generar_asiento_desde_factura(factura)
        logger.info(f"Asiento {asiento.id} generado para factura {factura.numero_factura}")
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
    """_registrar_pago_contable."""
    from apps.bookings.models import PagoVenta as PagoVentaModel

    try:
        pago = PagoVentaModel.objects.get(pk=pago_id)
        asiento = ContabilidadService.registrar_pago_y_diferencial(pago)
        if asiento:
            logger.info(f"Asiento de pago {asiento.id} generado para pago {pago_id}")
    except Exception as e:
        logger.error(f"Error registrando pago {pago_id}: {e}")


@receiver(reporte_proveedor_pdf_recibido)
def procesar_reporte_proveedor_pdf(sender, **kwargs):
    """
    Procesa un PDF de reporte de ventas de proveedor recibido por email.
    Escucha la señal reporte_proveedor_pdf_recibido (emitida por communications).
    Devuelve el ReporteVentaProveedor creado o None si no aplica.
    """
    try:
        from apps.contabilidad.supplier_report_service import SupplierReportProcessorService

        reporte = SupplierReportProcessorService.process_pdf_report(
            agencia=kwargs.get("agencia"),
            pdf_bytes=kwargs.get("pdf_bytes"),
            filename=kwargs.get("filename", ""),
            subject=kwargs.get("subject", ""),
            sender_email=kwargs.get("sender_email", ""),
        )
        return reporte
    except ValueError:
        return None
    except Exception as e:
        logger.error(f"Error procesando reporte de proveedor PDF: {e}", exc_info=True)
        return None

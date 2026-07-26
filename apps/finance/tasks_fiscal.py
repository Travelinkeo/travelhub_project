import logging

from celery import shared_task

from apps.finance.models_stubs import FacturaFiscal
from apps.finance.services.fiscal_provider_service import ElectronicInvoiceService

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=5,
    name="apps.finance.tasks.emitir_factura_electronica_task",
    queue="ia_heavy",
    time_limit=300,
    soft_time_limit=270,
)
def emitir_factura_electronica_task(self, venta_id, agencia_id=None):
    """emitir_factura_electronica_task."""
    from core.api import Agencia, agency_context, system_context

    try:
        if agencia_id:
            agencia = Agencia.objects.get(pk=agencia_id)
            ctx = agency_context(agencia)
        else:
            ctx = system_context()

        with ctx:
            fiscal = ElectronicInvoiceService.generar_y_firmar_xml(venta_id)
            ElectronicInvoiceService.enviar_proveedor_fiscal(fiscal)

            logger.info(
                f"✅ Factura Fiscal {fiscal.numero_factura} aprobada exitosamente para Venta ID {venta_id}"
            )

    except Exception as exc:
        logger.warning(
            f"⚠️ Error fiscal para Venta {venta_id}: {exc}. Reintentando ({self.request.retries}/{self.max_retries})..."
        )

        if self.request.retries >= self.max_retries:
            from core.api import system_context as sc

            with sc():
                fiscal = FacturaFiscal.objects.filter(venta_id=venta_id).first()
                if fiscal:
                    fiscal.estado_fiscal = FacturaFiscal.EstadoFiscal.RECHAZADA
                    fiscal.ultimo_mensaje_error = str(exc)
                    fiscal.save()

        raise self.retry(exc=exc, countdown=2**self.request.retries) from exc

    return True

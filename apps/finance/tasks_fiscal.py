import logging
from celery import shared_task
from django.db import transaction
from django.utils import timezone
from apps.finance.services.fiscal_provider_service import ElectronicInvoiceService
from apps.finance.models.fiscal import FacturaFiscal

logger = logging.getLogger(__name__)

@shared_task(
    bind=True, 
    max_retries=5, 
    name='apps.finance.tasks.emitir_factura_electronica_task', 
    queue='ia_heavy'
)
def emitir_factura_electronica_task(self, venta_id):
    """
    TAREA ASÍNCRONA DE FACTURACIÓN FISCAL:
    Maneja el firmado y envío al ente gubernamental.
    Incluye retries automáticos con backoff exponencial por si falla el servidor fiscal.
    """
    try:
        # 1. Generar y Firmar (Localmente)
        fiscal = ElectronicInvoiceService.generar_y_firmar_xml(venta_id)
        
        # 2. Enviar a la autoridad fiscal
        # Esta llamada puede fallar por Timeout de red (Ente Fiscal lento/caído)
        ElectronicInvoiceService.enviar_proveedor_fiscal(fiscal)
        
        logger.info(f"✅ Factura Fiscal {fiscal.numero_factura} aprobada exitosamente para Venta ID {venta_id}")

    except Exception as exc:
        # Reintento con backoff exponencial: 2, 4, 8, 16, 32 segundos de espera
        logger.warning(f"⚠️ Error fiscal para Venta {venta_id}: {exc}. Reintentando ({self.request.retries}/{self.max_retries})...")
        
        # Si ya llegamos al máximo de reintentos, marcar como rechazada
        if self.request.retries >= self.max_retries:
             fiscal = FacturaFiscal.objects.filter(venta_id=venta_id).first()
             if fiscal:
                 fiscal.estado_fiscal = FacturaFiscal.EstadoFiscal.RECHAZADA
                 fiscal.ultimo_mensaje_error = str(exc)
                 fiscal.save()
        
        # Lanzar reintento
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)

    return True

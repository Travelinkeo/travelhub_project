import logging
from celery import shared_task
from apps.finance.models import LinkDePago
from core.services.telegram_service import enviar_alerta_telegram

logger = logging.getLogger(__name__)

@shared_task(queue='notifications', max_retries=3)
def notificar_pago_zelle_task(link_id):
    """
    Se dispara cuando un cliente reporta un pago manual (Zelle/Transferencia)
    a través del Magic Link B2C.
    """
    try:
        link = LinkDePago.objects.select_related('venta__cliente', 'venta__agencia').get(id=link_id)
        venta = link.venta
        agencia = venta.agencia
        
        mensaje = (
            f"💸 *NUEVO PAGO REPORTADO*\n\n"
            f"🎫 *PNR:* {venta.localizador}\n"
            f"👤 *Cliente:* {venta.cliente.nombres.title()}\n"
            f"💰 *Monto a Conciliar:* {link.monto_total} {link.moneda}\n"
            f"🧾 *Referencia:* `{link.referencia_pago}`\n\n"
            f"⚡ *Acción Requerida:* Por favor, verifica tu estado de cuenta bancario y marca la venta como PAGADA en el Dashboard."
        )
        
        # Intentamos enviar a la agencia directamente si tiene canal, si no al general
        enviar_alerta_telegram(mensaje)
        logger.info(f"Notificación de pago enviada para Link {link_id}")
        return f"Notificación enviada (Ref: {link.referencia_pago})"
        
    except Exception as e:
        logger.error(f"Fallo enviando notificación de pago: {str(e)}")
        raise e

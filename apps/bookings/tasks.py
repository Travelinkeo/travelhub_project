import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(queue="notifications")
def notificar_pago_whatsapp_task(venta_id):
    """
    Tarea asincrona para notificar al cliente sobre su pago via WhatsApp.
    Multi-tenant: usa la instancia Evolution correcta por agencia (subdominio_slug).
    """
    from apps.bookings.models import Venta
    from apps.communications.services.whatsapp_service import send_whatsapp_message

    try:
        venta = Venta.all_objects.select_related("cliente", "moneda", "agencia").get(pk=venta_id)

        if not venta.cliente or not venta.cliente.telefono_principal:
            logger.warning(f"No se puede enviar WhatsApp para Venta {venta_id}: sin telefono")
            return False

        telefono = venta.cliente.telefono_principal
        localizador = venta.localizador or f"ID-{venta.pk}"
        monto = f"{venta.total_venta:,.2f} {venta.moneda.codigo_iso if venta.moneda else 'USD'}"
        cliente_nombre = venta.cliente.nombres

        mensaje = (
            f"Hola {cliente_nombre}! Hemos recibido con exito tu pago por "
            f"el localizador {localizador}. Monto procesado: {monto}. "
            f"Gracias por confiar en nosotros para tu viaje!"
        )

        logger.info(f"Enviando WhatsApp para Venta {venta_id} (agencia={venta.agencia})")
        resultado = send_whatsapp_message(telefono, mensaje, agencia=venta.agencia)

        return resultado.get("success", False)

    except Venta.DoesNotExist:
        logger.error(f"Venta {venta_id} no existe")
        return False
    except Exception as e:
        logger.exception(f"Error en notificar_pago_whatsapp_task Venta {venta_id}: {e}")
        return False

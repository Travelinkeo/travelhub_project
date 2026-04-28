from celery import shared_task
from django.utils.translation import gettext as _
import logging

# Importación diferida para evitar ciclos
# apps.bookings.models será importado dentro de la tarea

logger = logging.getLogger(__name__)

@shared_task(queue='notifications')
def notificar_pago_whatsapp_task(venta_id):
    """
    Tarea asíncrona para notificar al cliente sobre el recibo de su pago.
    Utiliza el carril de notificaciones aislado de Celery.
    """
    from apps.bookings.models import Venta
    from core.services.whatsapp import WhatsAppService

    try:
        # Usamos all_objects para asegurar que el trabajador de Celery pueda ver 
        # la venta independientemente del contexto de agencia (SaaS isolation bypass)
        venta = Venta.all_objects.select_related('cliente', 'moneda').get(pk=venta_id)
        
        if not venta.cliente or not venta.cliente.telefono_principal:
            logger.warning(f"⚠️ [CELERY] No se puede enviar WhatsApp para Venta {venta_id}: Cliente sin teléfono principal.")
            return False

        # Extraer datos para el mensaje
        telefono = venta.cliente.telefono_principal
        localizador = venta.localizador or f"ID-{venta.pk}"
        monto = f"{venta.total_venta:,.2f} {venta.moneda.codigo if venta.moneda else 'USD'}"
        cliente_nombre = venta.cliente.nombres
        
        # Multi-tenant: Definir nombre de instancia basado en la agencia (subdominio_slug o ID)
        agencia = venta.agencia
        instancia_name = f"TH_{agencia.subdominio_slug or agencia.id}"

        # Formatear el mensaje
        mensaje = (
            f"¡Hola {cliente_nombre}! 🌟 Hemos recibido con éxito tu pago por el localizador {localizador}. "
            f"Monto procesado: {monto}. ¡Gracias por confiar en nosotros para tu viaje! ✈️"
        )

        # Ejecutar el servicio multi-tenant
        logger.info(f"🚀 [CELERY] Ejecutando notificación de pago WhatsApp para Venta {venta_id} (Instancia: {instancia_name})")
        resultado = WhatsAppService.enviar_mensaje_texto(telefono, mensaje, instancia=instancia_name)
        
        return resultado.get('success', False)

    except Venta.DoesNotExist:
        logger.error(f"❌ [CELERY] Error: Venta {venta_id} no existe en la base de datos.")
        return False
    except Exception as e:
        logger.exception(f"🔥 [CELERY] Error inesperado en notificar_pago_whatsapp_task para Venta {venta_id}: {str(e)}")
        return False

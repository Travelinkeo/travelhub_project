# Archivo: core/services/parsing.py
"""Servicio de parsing para la aplicación automation.
"""

import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.automation.services.ticket_parser_service import TicketParserService

logger = logging.getLogger(__name__)


def procesar_boleto_importado_automatico(boleto):
    """
    Función Puente: Delega el trabajo al TicketParserService moderno.
    """
    boleto_id = boleto.pk
    logger.info(f"🚀 Iniciando orquestación para Boleto PK: {boleto_id}")

    try:
        # Instanciamos el servicio nuevo
        servicio = TicketParserService()
        venta = servicio.procesar_boleto(boleto_id)

        if venta:
            # Manejo de respuesta tipo Dict (Intercepción / Revisión)
            if isinstance(venta, dict):
                status = venta.get("status", "UNKNOWN")
                if status == "REVIEW_REQUIRED":
                    msg = "⚠️ Revisión Requerida: Falta información (bucle de intercepción)."
                    logger.info(msg)
                    return True, msg

                # Si es otro dict, logueamos advertencia pero no crash
                logger.warning(f"Respuesta inesperada tipo dict: {venta}")
                return True, str(venta)

            msg = f"✅ Éxito. Venta creada/actualizada PK: {venta.pk} - Monto: {venta.total_venta}"
            logger.info(msg)

            # Actualizamos el log del boleto
            boleto.refresh_from_db()
            boleto.log_parseo = msg
            boleto.save(update_fields=["log_parseo"])
            return True, msg
        else:
            msg = "⚠️ Servicio finalizó sin venta (Ver logs)."
            logger.warning(msg)
            return False, msg

    except Exception as e:
        logger.error(f"💥 Error en parsing.py: {e}", exc_info=True)
        try:
            boleto.estado_parseo = "ERR"
            boleto.log_parseo = f"Error de sistema: {str(e)}"
            boleto.save()
        except Exception as e:
            logger.warning(f"Excepción silenciosa capturada: {e}")
        return False, f"Error de sistema: {str(e)}"


# DISPARADOR AUTOMÁTICO
@receiver(post_save, sender="bookings.BoletoImportado")
def trigger_boleto_parse_service(sender, instance, created, **kwargs):
    """
    Dispara el pipeline de parseo cuando se crea un boleto nuevo en estado PEN.
    FIX: Ahora respeta are_signals_blocked() igual que el resto de señales del sistema,
    evitando que esta señal compita con el pipeline cuando ya tiene el lock de procesamiento.
    """
    from core.api import are_signals_blocked

    if are_signals_blocked():
        logger.info(
            f"⏭️ SIGNAL: Signals blocked. Bypassing trigger_boleto_parse_service para Boleto {instance.pk}"
        )
        return
    # Solo procesar si es nuevo, pendiente y tiene archivo adjunto
    if created and instance.estado_parseo == "PEN" and instance.archivo_boleto:
        procesar_boleto_importado_automatico(instance)

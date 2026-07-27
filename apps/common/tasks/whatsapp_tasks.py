import logging

from celery import shared_task
from django.conf import settings

from apps.common.utils.celery_utils import tenant_task

logger = logging.getLogger(__name__)


@tenant_task(
    name="core.tasks.enviar_notificacion_whatsapp_task",
    bind=True,
    max_retries=3,
    time_limit=120,
    soft_time_limit=90,
)
def enviar_notificacion_whatsapp_task(
    self,
    numero_cliente,
    mensaje,
    email_cliente=None,
    media_url=None,
    file_name=None,
    agencia_id=None,
    **kwargs,
):
    """enviar_notificacion_whatsapp_task."""
    from django.core.mail import send_mail

    from apps.communications.services.telegram_unified import enviar_alerta_telegram
    from apps.communications.services.whatsapp_unified import send_whatsapp_message

    agencia = None
    agencia_nombre = "TravelHub"

    if agencia_id:
        try:
            from core.models import Agencia

            agencia = Agencia.objects.get(id=agencia_id)
            agencia_nombre = agencia.nombre
        except Exception as exc:
            logger.debug("No se encontró agencia_id %s: %s", agencia_id, exc)

    if not agencia:
        from core.middleware import get_current_agency

        agencia = get_current_agency()
        agencia_nombre = agencia.nombre if agencia else "TravelHub"

    try:
        logger.info(
            f"Intentando enviar WhatsApp a {numero_cliente} (Intento {self.request.retries + 1}/4)"
        )

        respuesta = send_whatsapp_message(
            number=numero_cliente,
            text=mensaje,
            agencia=agencia,
            media_url=media_url,
            file_name=file_name,
        )

        if not respuesta.get("success"):
            raise Exception(f"WhatsApp Error: {respuesta.get('error_message', 'Unknown Error')}")

        logger.info(
            f"✅ WhatsApp enviado exitosamente a {numero_cliente} via {respuesta.get('provider')}"
        )
        return "Notificación enviada"

    except Exception as exc:
        retrasos_escalonados = [300, 900, 3600]

        if self.request.retries < self.max_retries:
            tiempo_espera = retrasos_escalonados[self.request.retries]
            raise self.retry(exc=exc, countdown=tiempo_espera) from exc
        else:
            logger.error(f"❌ Fallo definitivo enviando WhatsApp a {numero_cliente}.")

            alerta_agencia = (
                f"🚨 *FALLO WHATSAPP - {agencia_nombre}*\n\n"
                f"No se pudo entregar el mensaje a *{numero_cliente}*.\n"
                f"Detalle: {str(exc)}\n"
            )
            enviar_alerta_telegram(alerta_agencia)

            if email_cliente:
                try:
                    send_mail(
                        subject=f"Información de tu viaje - {agencia_nombre}",
                        message=f"Hola,\n\nIntentamos enviarte esta información por WhatsApp pero no fue posible. Aquí tienes los detalles:\n\n{mensaje}\n\nSaludos,\nEl equipo de {agencia_nombre}",
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[email_cliente],
                        fail_silently=True,
                    )
                except Exception as e:
                    logger.warning(f"Error sending fallback email to {email_cliente}: {e}")

            return "Fallo definitivo - Fallback ejecutado"


@shared_task(
    bind=True,
    queue="notifications",
    max_retries=3,
    default_retry_delay=10,
    time_limit=120,
    soft_time_limit=100,
)
def send_whatsapp_task(self, sender_id, recipient_number, message_text, agencia_id=None):
    """send_whatsapp_task."""
    from apps.communications.services.whatsapp_unified import enviar_whatsapp

    try:
        enviar_whatsapp(sender_id, message_text)
        logger.info(f"WhatsApp sent to {recipient_number or sender_id}")
        return True
    except Exception as exc:
        logger.error(f"WhatsApp task error: {exc}")
        self.retry(exc=exc)


@shared_task(
    bind=True,
    queue="notifications",
    max_retries=3,
    default_retry_delay=30,
    time_limit=120,
    soft_time_limit=100,
)
def send_factura_to_whatsapp_task(self, factura_id):
    """send_factura_to_whatsapp_task."""
    from apps.finance.models import Factura
    from apps.finance.services.factura_service import FacturaService

    try:
        factura = Factura.objects.get(pk=factura_id)
        result = FacturaService.send_to_whatsapp_if_needed(factura)
        if result:
            logger.info(f"Factura {factura_id} enviada a WhatsApp")
        return result
    except Exception as exc:
        logger.error(f"Error sending factura {factura_id} to WhatsApp: {exc}")
        self.retry(exc=exc)


@shared_task(
    bind=True,
    queue="default",
    max_retries=3,
    default_retry_delay=30,
    time_limit=120,
    soft_time_limit=100,
)
def download_twilio_media_task(self, media_url):
    """download_twilio_media_task."""
    from apps.automation.services.voice_parser_service import (
        download_twilio_media,
        extract_quote_intent_from_audio,
    )

    try:
        local_path = download_twilio_media(media_url)
        if not local_path:
            logger.error(f"Failed to download Twilio media: {media_url}")
            return None
        result = extract_quote_intent_from_audio(local_path)
        logger.info(f"Twilio media processed: {media_url}")
        return result
    except Exception as exc:
        logger.error(f"Twilio media task error: {exc}")
        self.retry(exc=exc)


@shared_task(
    bind=True,
    queue="notifications",
    max_retries=3,
    default_retry_delay=30,
    time_limit=60,
    soft_time_limit=50,
)
def send_whatsapp_meta_task(self, numero_cliente, mensaje, agencia_id=None):
    """send_whatsapp_meta_task."""
    from apps.communications.services.whatsapp_unified import enviar_mensaje_meta_api

    try:
        agencia = None
        if agencia_id:
            from core.models.agencia import Agencia

            agencia = Agencia.objects.get(pk=agencia_id)
        result = enviar_mensaje_meta_api(numero_cliente, mensaje, agencia=agencia)
        if result.get("success"):
            logger.info(f"Meta WhatsApp sent to {numero_cliente}")
        else:
            logger.warning(
                f"Meta WhatsApp failed for {numero_cliente}: {result.get('error_message')}"
            )
        return result
    except Exception as exc:
        logger.error(f"Meta WhatsApp task error: {exc}")
        self.retry(exc=exc)


@shared_task(
    bind=True,
    max_retries=2,
    default_retry_delay=10,
    time_limit=120,
    soft_time_limit=100,
)
def process_twilio_voice_quote_task(
    self, sender_id, raw_phone, body_text, num_media, media_url, media_type
):
    """
    Procesa un mensaje entrante de Twilio WhatsApp: transcripción de voz por IA,
    creación de cotización y envío de respuesta.
    """
    logger.info(f"Voice-to-Quote task: processing from {raw_phone}")

    try:
        from apps.cotizaciones.models import Cotizacion
        from apps.crm.models import Cliente

        cliente = Cliente.objects.filter(
            telefono_principal__icontains=raw_phone.lstrip("+")
        ).first()

        intencion_data = None
        has_media = bool(media_url)

        if media_url and ("audio" in media_type or "video" in media_type):
            from django.utils.module_loading import import_string

            process_twilio_audio_message = import_string(
                "apps.automation.services.voice_parser_service.process_twilio_audio_message"
            )
            intencion_data = process_twilio_audio_message(media_url)

        if not intencion_data and body_text and len(body_text) > 10:
            from django.utils.module_loading import import_string

            process_twilio_text_message = import_string(
                "apps.automation.services.voice_parser_service.process_twilio_text_message"
            )
            intencion_data = process_twilio_text_message(body_text)

        if not intencion_data or "error" in intencion_data:
            logger.info(f"Mensaje no parseable a cotización. Body: {body_text}")
            return

        try:
            pasajeros_str = intencion_data.get("numero_pasajeros", 1)
            try:
                pax = int(pasajeros_str)
            except (TypeError, ValueError):
                pax = 1

            destino_f = intencion_data.get("destino", "Varios")
            transcripcion = intencion_data.get("transcripcion", body_text)
            nota_interna = (
                f"[VOICE-TO-QUOTE IA] Intención: {intencion_data.get('intencion')}\n"
                f"Origen: {intencion_data.get('origen', 'N/D')}\n"
                f"Mes/Fecha: {intencion_data.get('mes_viaje', 'N/D')}\n"
                f"Tipo: {intencion_data.get('tipo', 'VARIO')}"
            )

            nueva_cot = Cotizacion()
            nueva_cot.destino = destino_f
            nueva_cot.numero_pasajeros = max(1, pax)
            nueva_cot.estado = Cotizacion.EstadoCotizacion.BORRADOR
            nueva_cot.descripcion_general = f"[TRANSCRITO]: {transcripcion}"
            nueva_cot.notas_internas = nota_interna
            nueva_cot.moneda_id = 1

            if cliente:
                nueva_cot.cliente = cliente
            else:
                nuevo_prospecto, _ = Cliente.objects.get_or_create(
                    telefono_principal=raw_phone,
                    defaults={
                        "nombres": "Prospecto",
                        "apellidos": raw_phone,
                        "tipo_cliente": "IND",
                        "email": f"{raw_phone.lstrip('+')}@whatsapp-lead.com",
                    },
                )
                nueva_cot.cliente = nuevo_prospecto
                nueva_cot.nombre_cliente_manual = "Prospecto Webhook"

            nueva_cot.save()
            logger.info(f"Cotización automatizada! ID: {nueva_cot.numero_cotizacion}")

            if has_media:
                respuesta = (
                    f"¡Hola! He escuchado tu audio completo. 🤖🎧\n"
                    f"Ya le he enviado tus datos a tu asesor para que analice "
                    f"las opciones de {destino_f}. ¡Te contactará por aquí mismo muy pronto!"
                )
            else:
                respuesta = (
                    f"¡Hola! He leído tu mensaje. 🤖📲\n"
                    f"En breve uno de nuestros especialistas procesará tu solicitud "
                    f"para {destino_f} y te enviará los detalles."
                )

            from apps.common.tasks import send_whatsapp_task

            send_whatsapp_task.delay(sender_id, sender_id, respuesta)

        except Exception as e:
            import traceback

            logger.error(f"Voice-To-Quote assembly error: {e}\n{traceback.format_exc()}")

    except Exception as exc:
        logger.error(f"Voice-to-Quote task error: {exc}")
        self.retry(exc=exc)

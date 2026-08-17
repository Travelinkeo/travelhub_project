import json
import logging
import os

import requests
from celery import shared_task
from django.core.cache import cache

from apps.common.utils.celery_utils import idempotent_task, tenant_task

logger = logging.getLogger(__name__)


@tenant_task(queue="notifications", time_limit=120, soft_time_limit=90)
@idempotent_task(timeout=1800, key_prefix="celery_notif_whatsapp")
def notificar_pago_whatsapp_task(venta_id, **kwargs):
    """notificar_pago_whatsapp_task."""
    from apps.bookings.models import Venta
    from apps.communications.services.whatsapp_unified import send_whatsapp_message

    try:
        try:
            venta = Venta.objects.select_related("cliente", "moneda", "agencia").get(pk=venta_id)
        except Venta.DoesNotExist:
            logger.error(f"Venta {venta_id} no existe")
            return False

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

    except Exception as e:
        logger.exception(f"Error en notificar_pago_whatsapp_task Venta {venta_id}: {e}")
        return False


# ==============================================================================
# 🛡️ COMPLIANCE GUARD & TIME LIMIT MONITOR TASKS
# ==============================================================================


def cls_notificar_infraccion_pasaporte(venta, pasajero, fecha_viaje):
    """cls_notificar_infraccion_pasaporte."""

    agencia = getattr(venta, "agencia", None)

    mensaje = (
        f"⚠️ <b>COMPLIANCE GUARD | INFRACCIÓN CRM</b>\n"
        f"---------------------------------------------\n"
        f"🚨 <b>Pasaporte en Riesgo de Rechazo</b>\n\n"
        f"• <b>Pasajero:</b> {pasajero.apellidos}, {pasajero.nombres}\n"
        f"• <b>Localizador Venta:</b> <code>{venta.localizador}</code>\n"
        f"• <b>Fecha del Viaje:</b> {fecha_viaje.strftime('%d/%m/%Y') if fecha_viaje else 'N/A'}\n"
        f"• <b>Vencimiento Pasaporte:</b> <b>{pasajero.fecha_vencimiento_pasaporte.strftime('%d/%m/%Y') if pasajero.fecha_vencimiento_pasaporte else 'N/A'}</b>\n"
        f"---------------------------------------------\n"
        f"❌ <i>El pasaporte cuenta con menos de 6 meses de vigencia obligatoria para la fecha del vuelo. Contactar de inmediato al cliente.</i>"
    )

    from apps.communications.services.telegram_unified import TelegramNotificationService

    buttons = [
        [
            {"text": "✅ Aprobar Excepción", "callback_data": f"approve_passport_{venta.id}"},
            {
                "text": "📋 Ver en TravelHub",
                "url": f"https://travelhub.cc/bookings/venta/{venta.id}/",
            },
        ]
    ]
    keyboard = TelegramNotificationService.build_inline_keyboard(buttons)
    TelegramNotificationService.send_message(mensaje, agencia=agencia, reply_markup=keyboard)


def cls_notificar_urgency_time_limit(venta):
    """cls_notificar_urgency_time_limit."""
    from django.conf import settings
    from django.utils import timezone

    bot_token = getattr(settings, "TELEGRAM_BOT_TOKEN", None)
    chat_id = getattr(
        settings, "TELEGRAM_FINANZAS_CHAT_ID", getattr(settings, "TELEGRAM_GROUP_ID", None)
    )

    if not bot_token or not chat_id:
        logger.warning("Telegram configuration missing for time limit notification")
        return

    # Calculamos minutos restantes de forma dinámica
    tiempo_restante = venta.tiempo_limite_emision - timezone.now()
    minutos_restantes = int(tiempo_restante.total_seconds() / 60)

    agencia_nombre = (
        venta.agencia.nombre.upper() if (venta.agencia and venta.agencia.nombre) else "TENANT"
    )

    mensaje = (
        f"⏰ <b>ALERTA CRÍTICA | TIME LIMIT EXPIRANDO</b>\n"
        f"---------------------------------------------\n"
        f"🛑 <b>Riesgo de Cancelación de Reserva</b>\n\n"
        f"• <b>Agencia Tenant:</b> {agencia_nombre}\n"
        f"• <b>Localizador GDS:</b> <code>{venta.localizador or venta.id_venta}</code>\n"
        f"• <b>Monto en Riesgo:</b> {venta.total_venta} USD\n"
        f"• <b>Expira en:</b> <pre>{minutos_restantes} minutos</pre>\n"
        f"• <b>Hora Límite (TL):</b> {venta.tiempo_limite_emision.strftime('%H:%M')} hrs\n"
        f"---------------------------------------------\n"
        f"🔥 <i>La reserva se cancelará automáticamente en el GDS si no se procesa la emisión o el pago garantizado en este lapso.</i>"
    )

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": mensaje,
        "parse_mode": "HTML",
        "reply_markup": {
            "inline_keyboard": [
                [
                    {
                        "text": "💵 Registrar Pago Rápido",
                        "url": f"https://travelhub.com/finance/venta/{venta.id_venta}/registrar-pago/",
                    }
                ]
            ]
        },
    }
    try:
        response = requests.post(url, json=payload, timeout=5)
        logger.info(f"Notification sent to Telegram (Time Limit). Status: {response.status_code}")
    except Exception as e:
        logger.error(f"Error sending Telegram notification: {e}")


@tenant_task(
    name="apps.bookings.tasks.verificar_cumplimiento_pasaportes_reserva_task",
    queue="notifications",
    time_limit=300,
    soft_time_limit=270,
)
def verificar_cumplimiento_pasaportes_reserva_task(venta_id, **kwargs):
    """verificar_cumplimiento_pasaportes_reserva_task."""
    from datetime import timedelta

    from apps.bookings.models import Venta

    try:
        from django.db.models import Prefetch

        from apps.bookings.models import SegmentoVuelo

        try:
            venta = (
                Venta.objects.select_related("agencia", "cliente")
                .prefetch_related(
                    "pasajeros",
                    Prefetch(
                        "segmentos_vuelo",
                        queryset=SegmentoVuelo.objects.filter(fecha_salida__isnull=False).order_by(
                            "fecha_salida"
                        ),
                        to_attr="segmentos_ordenados",
                    ),
                )
                .get(id_venta=venta_id)
            )
        except Venta.DoesNotExist:
            return f"Venta {venta_id} no encontrada."

        primer_segmento = venta.segmentos_ordenados[0] if venta.segmentos_ordenados else None
        if primer_segmento and primer_segmento.fecha_salida:
            primer_vuelo = primer_segmento.fecha_salida
        else:
            primer_vuelo = venta.fecha_venta

        if hasattr(primer_vuelo, "date"):
            primer_vuelo = primer_vuelo.date()

        fecha_limite_segura = primer_vuelo + timedelta(days=180)
        alertas_disparadas = 0

        for pasajero in venta.pasajeros.all():
            if not pasajero.fecha_vencimiento_pasaporte:
                continue

            if pasajero.fecha_vencimiento_pasaporte < fecha_limite_segura:
                alertas_disparadas += 1
                cls_notificar_infraccion_pasaporte(venta, pasajero, primer_vuelo)

        return f"Compliance Guard ejecutado para Venta {venta.localizador}. Alertas: {alertas_disparadas}"

    except Exception as e:
        logger.exception(f"Error en verificar_cumplimiento_pasaportes_reserva_task: {e}")
        return f"Error: {e}"


@tenant_task(
    name="apps.bookings.tasks.monitorear_tiempos_limite_periodico_task",
    queue="notifications",
    time_limit=300,
    soft_time_limit=270,
)
def monitorear_tiempos_limite_periodico_task(**kwargs):
    """monitorear_tiempos_limite_periodico_task."""
    from datetime import timedelta

    from django.utils import timezone

    from apps.bookings.models import Venta
    from core.api import Agencia, agency_context, get_current_agency

    agencia_activa = get_current_agency()

    ahora = timezone.now()
    umbral_critico = ahora + timedelta(hours=3)

    if agencia_activa:
        agencias = [agencia_activa]
    else:
        agencias = Agencia.objects.filter(activa=True).iterator(chunk_size=50)

    alertas_enviadas = 0
    for agencia in agencias:
        with agency_context(agencia):
            ventas_en_riesgo = Venta.objects.select_related("agencia").filter(
                estado__in=["PEN", "PAR"],
                tiempo_limite_emision__gt=ahora,
                tiempo_limite_emision__lte=umbral_critico,
                alerta_tl_disparada=False,
            )

            for venta in ventas_en_riesgo.iterator(chunk_size=200):
                cls_notificar_urgency_time_limit(venta)
                venta.alerta_tl_disparada = True
                venta.save(update_fields=["alerta_tl_disparada"])
                alertas_enviadas += 1

    return f"Monitor de Time Limits ejecutado. Reservas críticas detectadas y alertadas: {alertas_enviadas}"


@tenant_task(
    name="core.tasks.parsear_boleto_individual",
    time_limit=300,
    soft_time_limit=270,
    max_retries=3,
    default_retry_delay=60,
    acks_late=True,
)
def parsear_boleto_individual(boleto_id, **kwargs):
    """parsear_boleto_individual."""
    from apps.bookings.models import BoletoImportado

    try:
        boleto = BoletoImportado.objects.get(pk=boleto_id)
        ignore_manual = kwargs.get("ignore_manual", False)
        if not ignore_manual and boleto.estado_parseo in (
            BoletoImportado.EstadoParseo.COMPLETADO,
            BoletoImportado.EstadoParseo.ERROR_PARSEO,
        ):
            logger.info(
                f"⏭️ Boleto {boleto_id} ya fue procesado (estado: {boleto.estado_parseo}). Omitiendo."
            )
            return f"Boleto {boleto_id} ya procesado previamente."
    except BoletoImportado.DoesNotExist:
        return f"Boleto {boleto_id} no existe."

    try:
        from apps.automation.services.ticket_parser_service import TicketParserService

        logger.info(f" Iniciando tarea de parseo para Boleto {boleto_id} (Params: {kwargs})")
        service = TicketParserService()
        resultado = service.procesar_boleto(
            boleto_id,
            ignore_manual=kwargs.get("ignore_manual", True),
            bypass_cache=kwargs.get("bypass_cache", False),
        )
        if resultado:
            logger.info(f" Tarea de parseo completada para Boleto {boleto_id}")
            return f"Boleto {boleto_id} procesado exitosamente."
        else:
            logger.warning(f" Tarea de parseo finalizó sin resultados para Boleto {boleto_id}")
            return f"Fallo al procesar Boleto {boleto_id}"
    except Exception as e:
        logger.error(f" Error en parsear_boleto_individual: {e}")
        return f"Error: {e}"


@shared_task(
    name="core.tasks.retry_queued_boletos",
    time_limit=300,
    soft_time_limit=270,
    max_retries=2,
    default_retry_delay=600,
)
def retry_queued_boletos(agencia_id=None):
    """retry_queued_boletos."""
    from apps.bookings.models import BoletoImportado
    from apps.common.utils.celery_utils import safe_delay
    from core.middleware import agency_context
    from core.models import Agencia

    if agencia_id:
        agencias = [Agencia.objects.get(pk=agencia_id)]
    else:
        agencias = Agencia.objects.filter(activa=True).iterator(chunk_size=50)

    total_reencolados = 0
    for agencia in agencias:
        with agency_context(agencia):
            boletos_en_espera = BoletoImportado.objects.filter(
                estado_parseo=BoletoImportado.EstadoParseo.COLA_LLENA
            )
            for boleto in boletos_en_espera.iterator(chunk_size=200):
                task = safe_delay(parsear_boleto_individual, boleto.id_boleto_importado)
                if task:
                    boleto.estado_parseo = "PRO"
                    boleto.log_parseo = f"Re-encolado automáticamente por sistema de recuperación. TaskID: {task.id}"
                    boleto.save(update_fields=["estado_parseo", "log_parseo"])
                    total_reencolados += 1

    if total_reencolados == 0:
        return "No hay boletos en espera de cola."
    return f"Se re-encolaron {total_reencolados} boletos que estaban en espera."


@tenant_task(
    name="core.tasks.send_ticket_notification",
    time_limit=120,
    soft_time_limit=90,
    max_retries=3,
    default_retry_delay=120,
    acks_late=True,
)
def send_ticket_notification(boleto_id, **kwargs):
    """send_ticket_notification."""
    import os

    from django.conf import settings

    from apps.bookings.models import BoletoImportado

    try:
        boleto = BoletoImportado.objects.select_related("cliente", "agencia").get(
            id_boleto_importado=boleto_id
        )
        if hasattr(boleto, "notificacion_enviada") and boleto.notificacion_enviada:
            logger.info(f" Notificación ya enviada para Boleto {boleto_id}. Omitiendo.")
            return f"Notificación ya enviada para boleto {boleto_id}."
    except BoletoImportado.DoesNotExist:
        return f"Boleto con ID {boleto_id} no encontrado."

    try:
        from django.core.mail import EmailMessage

        logger.info(f"Iniciando envío de notificación para Boleto ID: {boleto_id}")

        if not boleto.archivo_pdf_generado:
            logger.warning(
                f"No se encontró PDF generado para el Boleto ID: {boleto_id}. No se puede enviar notificación."
            )
            return f"No hay PDF para el boleto {boleto_id}."

        recipient_email = boleto.cliente.email if boleto.cliente else None
        if not recipient_email:
            logger.error(
                f"El boleto {boleto_id} no tiene cliente con email. No se puede enviar notificación."
            )
            return "Destinatario no encontrado."

        if "@sin-email.com" in recipient_email.lower():
            logger.info(
                f"🔕 Notificación omitida para email de marcador de posición: {recipient_email}"
            )
            return "Omitido por ser email de marcador de posición"

        sender_name = boleto.agencia.nombre_comercial or boleto.agencia.nombre
        subject = f"Nuevo Boleto Procesado: {boleto.nombre_pasajero_completo} - PNR: {boleto.localizador_pnr}"

        body = (
            "Se ha procesado un nuevo boleto de viaje.\n\n"
            f"Pasajero: {boleto.nombre_pasajero_completo}\n"
            f"Localizador: {boleto.localizador_pnr}\n"
            f"Ruta: {boleto.ruta_vuelo}\n\n"
            "El boleto unificado se encuentra adjunto a este correo.\n\n"
            f"Saludos,\nEl equipo de {sender_name}"
        )

        email = EmailMessage(
            subject,
            body,
            settings.DEFAULT_FROM_EMAIL,
            [recipient_email],
        )

        boleto.archivo_pdf_generado.open(mode="rb")
        email.attach(
            os.path.basename(boleto.archivo_pdf_generado.name),
            boleto.archivo_pdf_generado.read(),
            "application/pdf",
        )
        boleto.archivo_pdf_generado.close()

        email.send()
        logger.info(f"Notificación para Boleto ID: {boleto_id} enviada a {recipient_email}.")
        return f"Notificación para boleto {boleto_id} enviada."

    except Exception as e:
        logger.exception(f"Fallo crítico al enviar notificación para Boleto ID {boleto_id}: {e}")
        raise e


@shared_task(
    name="core.tasks.check_upcoming_flights",
    time_limit=300,
    soft_time_limit=270,
    max_retries=2,
    default_retry_delay=600,
)
def check_upcoming_flights():
    """check_upcoming_flights."""
    from datetime import timedelta

    from django.conf import settings
    from django.utils import timezone

    from apps.bookings.models import BoletoImportado
    from apps.common.utils.celery_utils import safe_delay
    from apps.communications.services.telegram_unified import (
        TelegramNotificationService,
    )
    from core.middleware import agency_context
    from core.models.agencia import Agencia

    logger.info(" Buscando vuelos próximos para Check-in...")

    now = timezone.now()
    tomorrow_start = now + timedelta(hours=23)
    total_alerts = 0

    for agencia in Agencia.objects.filter(activa=True).iterator(chunk_size=50):
        with agency_context(agencia):
            boletos = BoletoImportado.objects.filter(
                agencia=agencia,
                fecha_subida__gte=now - timedelta(days=365),
                estado_parseo="COM",
                datos_parseados__icontains=tomorrow_start.strftime("%d %b").upper(),
            )

        chat_id = agencia.configuracion_api.get("TELEGRAM_GROUP_ID") or getattr(
            settings, "TELEGRAM_GROUP_ID", None
        )
        if not chat_id:
            continue

        for boleto in boletos.iterator(chunk_size=200):
            try:
                data = boleto.datos_parseados
                if isinstance(data, str):
                    data = json.loads(data)

                if "vuelos" in data and isinstance(data["vuelos"], list):
                    for vuelo in data["vuelos"]:
                        fecha_str = vuelo.get("fecha_salida") or vuelo.get("date")
                        target_date_str = tomorrow_start.strftime("%d %b")

                        if fecha_str and target_date_str.upper() in str(fecha_str).upper():
                            msg = (
                                f"⏰ <b>RECORDATORIO DE CHECK-IN</b>\n\n"
                                f"El vuelo de <b>{boleto.nombre_pasajero_completo}</b> sale mañana.\n"
                                f"✈️ Aerolínea: {boleto.aerolinea_emisora}\n"
                                f"📍 PNR: <code>{boleto.localizador_pnr}</code>\n"
                                f"📅 Fecha: {fecha_str}\n\n"
                                f"<i>Verifica si el Check-in está abierto.</i>"
                            )
                            TelegramNotificationService.send_message(
                                msg, chat_id=chat_id, agencia=agencia
                            )
                            total_alerts += 1
                            logger.info(
                                f"Alerta check-in enviada para {boleto.localizador_pnr} (Agencia: {agencia.nombre})"
                            )
                            try:
                                logger.info(
                                    f"📄 Generando PDF para Boleto {boleto.pk} (asynchronously)..."
                                )
                                safe_delay(generar_pdf_ticket_async_task, boleto.pk)
                            except Exception as e_pdf_gen:
                                logger.error(
                                    f"❌ Error encolando generación de PDF para Boleto {boleto.pk}: {e_pdf_gen}"
                                )
                            break
            except Exception as e:
                logger.error(f"Error procesando boleto {boleto.pk} para checkin: {e}")

    result = f"Check-in scan completado. Alertas enviadas: {total_alerts}"
    logger.info(result)
    return result


@shared_task(
    name="core.tasks.enviar_recordatorios_vuelo_task",
    time_limit=300,
    soft_time_limit=270,
)
def enviar_recordatorios_vuelo_task():
    """Envía recordatorios de vuelo 24h antes por WhatsApp al cliente"""
    from datetime import timedelta

    from django.utils import timezone

    from apps.bookings.models import BoletoImportado
    from apps.communications.services.notification_dispatcher import (
        enviar_recordatorio_vuelo,
    )
    from core.middleware import agency_context
    from core.models.agencia import Agencia

    now = timezone.now()
    window_start = now + timedelta(hours=20)
    window_end = now + timedelta(hours=28)

    total_enviados = 0

    for agencia in Agencia.objects.filter(activa=True).iterator(chunk_size=50):
        try:
            with agency_context(agencia):
                boletos = BoletoImportado.objects.filter(
                    agencia=agencia,
                    estado_parseo="COM",
                    venta_asociada__isnull=False,
                    datos_parseados__isnull=False,
                )

                for boleto in boletos.iterator(chunk_size=100):
                    try:
                        datos = boleto.datos_parseados
                        if isinstance(datos, str):
                            datos = json.loads(datos)

                        normalized = datos.get("normalized", datos)
                        flights = normalized.get("flights", [])
                        if not flights:
                            continue

                        for flight in flights:
                            fecha_str = flight.get("date", "")
                            hora_str = flight.get("time", "00:00")
                            if not fecha_str:
                                continue

                            try:
                                from django.utils.dateparse import parse_date, parse_time

                                fecha_vuelo = parse_date(fecha_str)
                                hora_vuelo = parse_time(hora_str) if hora_str else None
                                if not fecha_vuelo:
                                    continue

                                import datetime

                                from django.utils.timezone import make_aware

                                dt_vuelo = make_aware(
                                    datetime.datetime.combine(
                                        fecha_vuelo,
                                        hora_vuelo or datetime.time(0, 0),
                                    )
                                )

                                if window_start <= dt_vuelo <= window_end:
                                    enviar_recordatorio_vuelo(boleto, horas_antes=24)
                                    total_enviados += 1
                                    break
                            except Exception as exc:
                                logger.debug("Ignored exception parsing reminder date: %s", exc)
                                continue
                    except Exception as e:
                        logger.error(f"Error procesando boleto {boleto.pk} para recordatorio: {e}")
        except Exception as e:
            logger.error(f"Error en agencia {agencia.nombre} para recordatorios: {e}")

    result = f"Recordatorios de vuelo enviados: {total_enviados}"
    logger.info(result)
    return result


@tenant_task(
    name="core.tasks.generar_pdf_ticket_async_task",
    time_limit=180,
    soft_time_limit=150,
    max_retries=3,
    default_retry_delay=30,
    acks_late=True,
)
def generar_pdf_ticket_async_task(boleto_id, **kwargs):
    """generar_pdf_ticket_async_task."""
    import time

    from django.core.files.base import ContentFile

    from apps.automation.parsers.normalization import DataNormalizationService
    from apps.automation.parsers.pdf_generation import PdfGenerationService
    from apps.bookings.models import BoletoImportado

    logger.info(f" Iniciando tarea asíncrona para generar PDF de Boleto {boleto_id}")
    try:
        boleto = BoletoImportado.objects.select_related("agencia").get(pk=boleto_id)
    except BoletoImportado.DoesNotExist:
        logger.error(f" Boleto {boleto_id} no encontrado para generar PDF.")
        return f"Boleto {boleto_id} no encontrado."

    fname = (
        os.path.basename(boleto.archivo_pdf_generado.name)
        if boleto.archivo_pdf_generado
        else f"Boleto_{boleto.pk}.pdf"
    )

    force = kwargs.get("force", True)
    if not boleto.archivo_pdf_generado or force:
        if not boleto.datos_parseados:
            logger.warning(
                f"⚠️ El boleto {boleto_id} no tiene datos parseados. No se puede generar PDF."
            )
            return f"Sin datos parseados para boleto {boleto_id}."

        try:
            logger.info(f" Generando TKT PDF asíncrono para Boleto {boleto.pk}")
            pdf_start = time.time()
            datos_norm = DataNormalizationService.normalize_ticket_data(boleto.datos_parseados)
            pdf_bytes, fname = PdfGenerationService.generate_ticket(
                datos_norm, agencia_obj=boleto.agencia, boleto_obj=boleto
            )
            pdf_duration = time.time() - pdf_start
            logger.info(f" [PROFILING] PDF Generation duration (asíncrono): {pdf_duration:.2f}s")

            if pdf_bytes and len(pdf_bytes) > 100:
                boleto.archivo_pdf_generado.save(fname, ContentFile(pdf_bytes), save=True)
                logger.info(f" PDF guardado (asíncrono): {fname} ({len(pdf_bytes)} bytes)")

                if boleto.estado_parseo == BoletoImportado.EstadoParseo.ERROR_PARSEO:
                    es_parcial = bool(datos_norm.get("_requiere_revision", False))
                    boleto.estado_parseo = (
                        BoletoImportado.EstadoParseo.REVISION_REQUERIDA
                        if es_parcial
                        else BoletoImportado.EstadoParseo.COMPLETADO
                    )
                    boleto.save(update_fields=["estado_parseo"])
            else:
                logger.warning(
                    f"⚠️ PDF generado vacío o muy pequeño ({len(pdf_bytes) if pdf_bytes else 0} bytes). "
                    f"Marcando boleto {boleto_id} como ERROR para que la UI muestre botón de reintento."
                )
                try:
                    BoletoImportado.objects.filter(pk=boleto_id).update(
                        estado_parseo=BoletoImportado.EstadoParseo.ERROR_PARSEO,
                        log_parseo=f"PDF vacío generado ({len(pdf_bytes) if pdf_bytes else 0} bytes). Usa Reintentar.",
                    )
                except Exception as e_upd:
                    logger.error(f"No se pudo marcar boleto {boleto_id} como ERR: {e_upd}")
                return f"PDF vacío generado para boleto {boleto_id}."
        except Exception as e:
            logger.exception(f"❌ Error en tarea asíncrona de PDF para Boleto {boleto_id}: {e}")
            try:
                BoletoImportado.objects.filter(pk=boleto_id).update(
                    estado_parseo=BoletoImportado.EstadoParseo.ERROR_PARSEO,
                    log_parseo=f"Error en generación de PDF: {str(e)}",
                )
            except Exception as e_inner:
                logger.error(
                    f"No se pudo actualizar estado_parseo a ERR para boleto {boleto_id}: {e_inner}"
                )
            raise e

    # 🚀 ENVIAR NOTIFICACIONES TELEGRAM Y WHATSAPP AUTOMÁTICAMENTE (Con Lock de Idempotencia)
    notif_lock_key = f"notif_sent_boleto_{boleto.pk}"
    if cache.add(notif_lock_key, "1", timeout=300) or kwargs.get("force_notification"):
        try:
            agencia = boleto.agencia or (
                boleto.venta_asociada.agencia if boleto.venta_asociada else None
            )
            pnr = boleto.localizador_pnr or "N/A"
            pasajero = (
                boleto.nombre_pasajero_procesado or boleto.nombre_pasajero_completo or "Pasajero"
            )
            caption = (
                f"✈️ <b>Boleto Confirmado</b>\n\n"
                f"👤 <b>Pasajero:</b> {pasajero}\n"
                f"📌 <b>PNR:</b> {pnr}\n"
                f"🎟️ <b>Boleto:</b> {boleto.numero_boleto or 'N/A'}\n"
                f"🏢 <b>Agencia:</b> {agencia.nombre if agencia else 'TravelHub'}"
            )

            # 1. Dispatch Telegram Notification
            from apps.common.tasks.telegram_tasks import send_telegram_document_task

            if hasattr(boleto.archivo_pdf_generado, "path") and os.path.exists(
                boleto.archivo_pdf_generado.path
            ):
                pdf_path = boleto.archivo_pdf_generado.path
            else:
                pdf_path = boleto.archivo_pdf_generado.url

            send_telegram_document_task.delay(
                file_path=pdf_path,
                caption=caption,
                agencia_id=agencia.id if agencia else None,
            )
            logger.info(f"📲 Notificación de Telegram encolada para Boleto {boleto.pk}")

            # 2. Dispatch WhatsApp Notification
            cliente = (
                getattr(boleto.venta_asociada, "cliente", None) if boleto.venta_asociada else None
            )
            telefono_cliente = getattr(cliente, "telefono_principal", None) if cliente else None
            if not telefono_cliente:
                telefono_cliente = (
                    getattr(cliente, "telefono_secundario", None) if cliente else None
                )

            telefono_agencia = getattr(agencia, "whatsapp", None) if agencia else None
            ws_caption = f"✈️ *Boleto Confirmado* — {pasajero}\n📌 PNR: {pnr}\n🎟️ N° Boleto: {boleto.numero_boleto or 'N/A'}"
            try:
                from apps.communications.services.whatsapp_service import WhatsAppService

                pdf_url = boleto.archivo_pdf_generado.url

                if agencia and telefono_agencia:
                    ws = WhatsAppService(agencia_id=agencia.id)
                    ws.send_document(
                        phone_number=telefono_agencia,
                        document_url_or_base64=pdf_url,
                        filename=fname,
                        caption=ws_caption,
                    )
                    logger.info(
                        f"💬 PDF enviado por WhatsApp a agencia ({telefono_agencia}) para Boleto {boleto.pk}"
                    )

                if telefono_cliente and agencia and telefono_cliente != telefono_agencia:
                    ws = WhatsAppService(agencia_id=agencia.id)
                    ws.send_document(
                        phone_number=telefono_cliente,
                        document_url_or_base64=pdf_url,
                        filename=fname,
                        caption=f"Estimado/a {pasajero}, adjuntamos su boleto electrónico PNR {pnr}.",
                    )
                    logger.info(
                        f"💬 PDF enviado por WhatsApp a cliente ({telefono_cliente}) para Boleto {boleto.pk}"
                    )
            except Exception as e_ws:
                logger.error(f"⚠️ Error enviando PDF por WhatsApp para Boleto {boleto.pk}: {e_ws}")
        except Exception as e_notif:
            logger.error(
                f"⚠️ Error enviando notificaciones automáticas de Telegram/WhatsApp: {e_notif}"
            )

    return f"PDF procesado y notificado para boleto {boleto_id}."


@shared_task(queue="celery", time_limit=300)
def retry_queued_boletos_task():
    """
    Tarea periódica (P3-001) que busca boletos en estado QUE (Cola Llena)
    y los vuelve a encolar para parseo asíncrono.
    """
    from apps.bookings.models import BoletoImportado
    from core.api import parsear_boleto_individual
    from core.middleware import system_context

    logger.info(" Iniciando reintento de boletos encolados en estado QUE (Cola Llena)...")

    # 🔓 system_context obligatorio con motivo para bypassear RLS
    with system_context(reason="retry_queued_boletos"):
        boletos_stuck = BoletoImportado.all_objects.filter(
            estado_parseo=BoletoImportado.EstadoParseo.COLA_LLENA, is_deleted=False
        ).order_by("fecha_subida")[:50]

        count = 0
        for boleto in boletos_stuck:
            logger.info(f" Re-encolando boleto stuck ID={boleto.pk} (Agencia: {boleto.agencia})")
            # Cambiar a PRO para que no sea seleccionado de nuevo en la siguiente iteración
            BoletoImportado.all_objects.filter(pk=boleto.pk).update(
                estado_parseo=BoletoImportado.EstadoParseo.EN_PROCESO,
                log_parseo="Re-encolado automático por tarea programada.",
            )
            parsear_boleto_individual.delay(boleto.pk)
            count += 1

        if count > 0:
            logger.info(f" Se re-encolaron {count} boletos que estaban en cola de espera.")
        else:
            logger.info(" No se encontraron boletos en estado QUE (Cola Llena).")

        return count


# ==============================================================================
# 📬 BANDEJA CONVERSACIONAL Y DESPACHO DE MENSAJES RFC 2822 / WHATSAPP
# ==============================================================================


@shared_task(queue="notifications", bind=True, max_retries=3, default_retry_delay=60)
def dispatch_booking_message_task(
    self, message_id: int, attach_ticket: bool = False, include_itinerary_link: bool = True
):
    """
    Despacha un mensaje de venta en segundo plano:
    1. Construye el correo RFC 2822 con Message-ID e In-Reply-To para preservar el hilo.
    2. Si attach_ticket=True, compila o asocia el PDF del boleto generado.
    3. Si el canal es WHATSAPP o el cliente tiene teléfono, envía la notificación correspondiente.
    """
    from django.conf import settings
    from django.core.mail import EmailMessage

    from apps.bookings.models import BoletoImportado, MensajeAdjunto, VentaMensaje
    from apps.communications.services.whatsapp_unified import send_whatsapp_message
    from core.middleware import system_context

    with system_context(reason="dispatch_booking_message"):
        try:
            msg_record = VentaMensaje.objects.select_related(
                "venta", "venta__agencia", "venta__cliente"
            ).get(id=message_id)
            venta = msg_record.venta
            agencia = venta.agencia

            cuerpo_completo = msg_record.cuerpo

            # Anexar enlace a Ficha Digital si existe
            if msg_record.enlace_ficha_digital:
                cuerpo_completo += f"\n\n📱 Ver tu Ficha Digital e Itinerario en Vivo:\n{msg_record.enlace_ficha_digital}"

            # 1. Despacho por Correo Electrónico
            if msg_record.canal == "EMAIL" or "@" in msg_record.destinatario:
                remitente_email = getattr(
                    settings, "DEFAULT_FROM_EMAIL", "operaciones@travelhub.cc"
                )
                subject = f"Itinerario de Viaje - Localizador {venta.localizador}"

                headers = {
                    "Message-ID": msg_record.message_id,
                }
                if msg_record.in_reply_to:
                    headers["In-Reply-To"] = msg_record.in_reply_to
                    headers["References"] = msg_record.in_reply_to

                email = EmailMessage(
                    subject=subject,
                    body=cuerpo_completo,
                    from_email=remitente_email,
                    to=[msg_record.destinatario],
                    headers=headers,
                )

                # Anexar PDF del boleto si fue solicitado
                if attach_ticket:
                    # Buscar boleto PDF existente en la venta o boleto importado
                    boleto = (
                        BoletoImportado.objects.filter(venta=venta, archivo_pdf__isnull=False)
                        .exclude(archivo_pdf="")
                        .first()
                    )
                    if boleto and boleto.archivo_pdf:
                        try:
                            pdf_content = boleto.archivo_pdf.read()
                            filename = f"Boleto_{venta.localizador}.pdf"
                            email.attach(filename, pdf_content, "application/pdf")

                            # Guardar en adjuntos del mensaje
                            MensajeAdjunto.objects.get_or_create(
                                mensaje=msg_record,
                                nombre_archivo=filename,
                                tipo_documento="BOLETO",
                                defaults={"archivo": boleto.archivo_pdf},
                            )
                        except Exception as pdf_err:
                            logger.warning(
                                f"No se pudo adjuntar PDF para Venta {venta.localizador}: {pdf_err}"
                            )

                email.send(fail_silently=False)
                logger.info(
                    f"✅ Correo despachado exitosamente a {msg_record.destinatario} para Venta {venta.localizador}"
                )

            # 2. Despacho por WhatsApp si es el canal seleccionado
            elif msg_record.canal == "WHATSAPP":
                if msg_record.destinatario:
                    send_whatsapp_message(
                        phone=msg_record.destinatario, message=cuerpo_completo, agencia=agencia
                    )
                    logger.info(
                        f"✅ WhatsApp despachado a {msg_record.destinatario} para Venta {venta.localizador}"
                    )

            return True

        except Exception as exc:
            logger.error(f"❌ Error despachando mensaje {message_id}: {exc}")
            raise self.retry(exc=exc) from exc

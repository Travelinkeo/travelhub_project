import base64
import datetime
import logging
import os
from email.header import decode_header
from io import BytesIO

from celery import shared_task
from django.conf import settings

from apps.common.utils.celery_utils import idempotent_task, tenant_task

logger = logging.getLogger(__name__)


def get_filename_from_header(header):
    if not header:
        return None
    decoded_header = decode_header(header)
    parts = []
    for part, charset in decoded_header:
        if isinstance(part, bytes):
            try:
                parts.append(part.decode(charset or "utf-8", errors="ignore"))
            except (UnicodeDecodeError, LookupError):
                parts.append(part.decode("latin-1", errors="ignore"))
        else:
            parts.append(part)
    return "".join(parts)


@shared_task(
    name="core.tasks.procesar_correo_individual_agencia", time_limit=300, soft_time_limit=270
)
def procesar_correo_individual_agencia(agencia_id):
    from apps.communications.services.email_unified import EmailMonitorService
    from core.middleware import agency_context
    from core.models.agencia import Agencia

    try:
        agencia = Agencia.objects.get(pk=agencia_id)
        config = agencia.configuracion
        if not config:
            return f"Agencia {agencia_id} no configurada."

        email_user = config.email_monitor_user or config.correo_emisiones
        email_pass = config.email_monitor_password or config.password_app_correo
        if not email_user or not email_pass:
            return f"Agencia {agencia_id} no configurada (falta usuario/contraseña de monitoreo)."

        with agency_context(agencia):
            logger.info(f"🔄 Procesando agencia SaaS (individual): {agencia.nombre} ({email_user})")

            monitor = EmailMonitorService(
                agencia=agencia, notification_type="telegram", process_all=False, mark_as_read=True
            )

            cantidad = monitor.procesar_una_vez()

            if cantidad and cantidad > 0:
                canal = getattr(config, "canal_notificaciones_mailbot", "telegram")
                _notificar_operador(agencia, cantidad, canal)

            return f"Agencia {agencia.nombre} procesada con éxito. {cantidad} correos procesados."
    except Exception as e:
        logger.error(f"❌ Error procesando agencia {agencia_id} en paralelo: {e}")
        raise


def _notificar_operador(agencia, cantidad_correos, canal="telegram"):
    """Notifica al operador según el canal configurado (telegram/whatsapp/both/none)"""
    if canal == "none":
        return

    if canal in ("telegram", "both"):
        _notificar_operador_telegram(agencia, cantidad_correos)

    if canal in ("whatsapp", "both"):
        _notificar_operador_whatsapp(agencia, cantidad_correos)


def _notificar_operador_telegram(agencia, cantidad_correos):
    """Notifica al operador por Telegram cuando se detectan correos nuevos"""
    try:
        config = agencia.configuracion
        bot_token = getattr(config, "telegram_bot_token", None) or getattr(
            agencia, "telegram_bot_token", None
        )
        chat_id = getattr(config, "telegram_chat_id", None) or getattr(
            agencia, "telegram_chat_id", None
        )

        if not bot_token or not chat_id:
            logger.debug(
                f"Agencia {agencia.nombre} sin Telegram configurado. Saltando notificación."
            )
            return

        from apps.common.tasks import send_telegram_task

        mensaje = (
            f"📬 *Reporte de Monitoreo de Correo*\n\n"
            f"Se detectaron *{cantidad_correos}* correo(s) nuevo(s) en tu bandeja de emisiones.\n\n"
            f"_Revisá tu dashboard para más detalles._\n"
            f"_Tu agencia: {agencia.nombre}_"
        )

        send_telegram_task.delay(message=mensaje, chat_id=chat_id)
        logger.info(f"✅ Telegram de monitoreo enviado a operador de {agencia.nombre}")
    except Exception as e:
        logger.warning(f"⚠️ No se pudo enviar Telegram al operador de {agencia.nombre}: {e}")


def _notificar_operador_whatsapp(agencia, cantidad_correos):
    """Notifica al operador por WhatsApp cuando se detectan correos nuevos"""
    try:
        telefono = getattr(agencia, "whatsapp", None)
        if not telefono:
            logger.debug(
                f"Agencia {agencia.nombre} sin número WhatsApp configurado. Saltando notificación."
            )
            return

        from apps.communications.services.whatsapp_unified import enviar_whatsapp

        mensaje = (
            f"📬 *Reporte de Monitoreo de Correo*\n\n"
            f"Se detectaron *{cantidad_correos}* correo(s) nuevo(s) en tu bandeja de emisiones.\n\n"
            f"_Revisá tu dashboard para más detalles._\n"
            f"_Tu agencia: {agencia.nombre}_"
        )

        enviar_whatsapp(telefono, mensaje, agencia=agencia)
        logger.info(f"✅ WhatsApp de monitoreo enviado a operador de {agencia.nombre}")
    except Exception as e:
        logger.warning(f"⚠️ No se pudo enviar WhatsApp al operador de {agencia.nombre}: {e}")


@shared_task(
    name="core.tasks.process_incoming_emails",
    time_limit=600,
    soft_time_limit=540,
    max_retries=3,
    default_retry_delay=300,
    acks_late=True,
)
def process_incoming_emails():
    from django.core.cache import cache
    from django.db.models import Q

    from core.models.agencia import Agencia

    lock_key = "lock:process_incoming_emails"
    if not cache.add(lock_key, "locked", timeout=600):
        logger.warning("Solapamiento detectado: tarea ya en ejecución")
        return "Solapamiento evitado."

    try:
        logger.info(
            "🚀 Iniciando tarea programada: Procesamiento de Correos (Multi-Tenant, Paralelizado)"
        )

        agencias_qs = (
            Agencia.objects.filter(activa=True)
            .filter(configuracion__email_monitor_active=True)
            .filter(
                (
                    Q(configuracion__email_monitor_user__isnull=False)
                    & ~Q(configuracion__email_monitor_user="")
                )
                | (
                    Q(configuracion__correo_emisiones__isnull=False)
                    & ~Q(configuracion__correo_emisiones="")
                )
            )
        )

        if not agencias_qs.exists():
            logger.warning("No hay agencias activas para monitorear.")
            return "Sin agencias activas."

        total_agencias = 0
        for agencia in agencias_qs.iterator(chunk_size=50):
            config = agencia.configuracion
            if not config:
                continue
            has_email = config.email_monitor_user or config.correo_emisiones
            has_pass = config.email_monitor_password or config.password_app_correo
            if not has_email or not has_pass:
                continue

            procesar_correo_individual_agencia.delay(agencia.id)
            total_agencias += 1

        resultado = (
            f"Se despacharon tareas de procesamiento en paralelo para {total_agencias} agencias."
        )
        logger.info(resultado)
        return resultado
    finally:
        cache.delete(lock_key)


@tenant_task(
    name="core.tasks.enviar_notificacion_whatsapp_task",
    bind=True,
    max_retries=3,
    time_limit=120,
    soft_time_limit=90,
)
def enviar_notificacion_whatsapp_task(
    self, numero_cliente, mensaje, email_cliente=None, media_url=None, file_name=None, **kwargs
):
    from django.core.mail import send_mail

    from apps.communications.services.telegram_unified import enviar_alerta_telegram
    from apps.communications.services.whatsapp_unified import send_whatsapp_message
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


@tenant_task(
    name="core.tasks.migrar_logos_agencia_task",
    time_limit=600,
    soft_time_limit=540,
    max_retries=2,
    default_retry_delay=600,
)
def migrar_logos_agencia_task(agencia_id, **kwargs):
    from apps.communications.services.telegram_unified import upload_logo_to_telegram
    from core.models.agencia import Agencia

    try:
        agencia = Agencia.objects.get(pk=agencia_id)
    except Agencia.DoesNotExist:
        return f"Agencia {agencia_id} no encontrada."

    branding = agencia.branding
    if not branding:
        return f"Agencia {agencia_id} no tiene componente de branding."

    updated_fields = []

    if branding.logo and not branding.logo_telegram_id:
        try:
            fid = upload_logo_to_telegram(branding.logo.file, branding.logo.name)
            if fid:
                branding.logo_telegram_id = fid
                branding.logo_base64 = None
                updated_fields.extend(["logo_telegram_id", "logo_base64"])
        except Exception as e:
            logger.error(f"Error subiendo logo a Telegram para Agencia {agencia_id}: {e}")

    logos_to_migrate = [
        ("logo_base64", "logo_general"),
        ("logo_pdf_base64", "logo_pdf_light"),
        ("logo_pdf_dark_base64", "logo_pdf_dark"),
    ]

    for field_name, prefix in logos_to_migrate:
        val = getattr(branding, field_name, None)
        if val and len(val) > 1000:
            try:
                if ";base64," in val:
                    header, data = val.split(";base64,")
                else:
                    data = val

                decoded = base64.b64decode(data)
                fid = upload_logo_to_telegram(
                    BytesIO(decoded), f"{prefix}_{agencia.rif or agencia.pk}.png"
                )
                if fid:
                    if field_name == "logo_base64":
                        branding.logo_telegram_id = fid
                        branding.logo_base64 = None
                        updated_fields.extend(["logo_telegram_id", "logo_base64"])
            except Exception as e:
                logger.error(
                    f"Error migrando {field_name} a Telegram para Agencia {agencia_id}: {e}"
                )

    if updated_fields:
        branding.save(update_fields=list(set(updated_fields)))
        return f"Branding de Agencia {agencia_id} actualizado: {updated_fields}"


@shared_task(
    name="core.tasks.cleanup_temporary_storage_files",
    time_limit=300,
    soft_time_limit=270,
    max_retries=2,
    default_retry_delay=3600,
)
def cleanup_temporary_storage_files(days=7):
    from django.core.files.storage import default_storage
    from django.utils import timezone

    logger.info(f"🧹 Iniciando limpieza de archivos temporales (Antigüedad > {days} días)...")

    prefixes = ["temp/", "tmp/", "vouchers_tmp/"]
    count = 0
    deleted_size = 0

    threshold = timezone.now() - datetime.timedelta(days=days)

    for prefix in prefixes:
        try:
            dirs, files = default_storage.listdir(prefix)

            for filename in files:
                filepath = os.path.join(prefix, filename)
                try:
                    mtime = default_storage.get_modified_time(filepath)

                    if mtime < threshold:
                        size = default_storage.size(filepath)
                        default_storage.delete(filepath)
                        count += 1
                        deleted_size += size
                        logger.debug(f"🗑️ Eliminado: {filepath} ({size} bytes)")
                except Exception as e:
                    logger.error(f"⚠️ No se pudo procesar/borrar {filepath}: {e}")

        except Exception as e:
            logger.warning(f"⚠️ Error accediendo al prefijo {prefix}: {e}")

    result = f"Limpieza completada. Se eliminaron {count} archivos ({deleted_size / 1024:.2f} KB)."
    logger.info(result)
    return result


@shared_task(
    bind=True,
    queue="notifications",
    max_retries=3,
    default_retry_delay=10,
    time_limit=60,
    soft_time_limit=50,
)
def send_telegram_task(self, message, chat_id=None, parse_mode="HTML", agencia_id=None):
    from apps.communications.services.telegram_unified import TelegramNotificationService

    try:
        agencia = None
        if agencia_id:
            from core.models.agencia import Agencia

            agencia = Agencia.objects.get(pk=agencia_id)
        success = TelegramNotificationService.send_message(
            message, chat_id=chat_id, parse_mode=parse_mode, agencia=agencia
        )
        if success:
            logger.info(f"Telegram notification sent (chat={chat_id or 'default'})")
        else:
            logger.warning(f"Telegram notification failed (chat={chat_id or 'default'})")
        return success
    except Exception as exc:
        logger.error(f"Telegram task error: {exc}")
        self.retry(exc=exc)


@shared_task(
    bind=True,
    queue="notifications",
    max_retries=3,
    default_retry_delay=10,
    time_limit=120,
    soft_time_limit=100,
)
def send_whatsapp_task(self, sender_id, recipient_number, message_text, agencia_id=None):
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
    default_retry_delay=10,
    time_limit=60,
    soft_time_limit=50,
)
def send_email_task(self, recipient, subject, message, from_email=None, agencia_id=None, **kwargs):
    from apps.communications.services.email_unified import enviar_email_generico

    try:
        agencia = None
        if agencia_id:
            from core.models.agencia import Agencia

            agencia = Agencia.objects.get(pk=agencia_id)
        enviar_email_generico(
            destinatario=recipient,
            asunto=subject,
            mensaje=message,
            from_email=from_email,
            agencia=agencia,
        )
        logger.info(f"Email sent to {recipient}")
        return True
    except Exception as exc:
        logger.error(f"Email task error: {exc}")
        self.retry(exc=exc)


@shared_task(
    bind=True,
    queue="notifications",
    max_retries=3,
    default_retry_delay=30,
    time_limit=60,
    soft_time_limit=50,
)
def enviar_bienvenida_agencia_task(self, agencia_id, user_id):
    from django.contrib.auth import get_user_model

    from apps.communications.services.notification_dispatcher import NotificationService
    from core.models.agencia import Agencia

    User = get_user_model()
    try:
        agencia = Agencia.objects.get(pk=agencia_id)
        user = User.objects.get(pk=user_id)
        NotificationService.enviar_bienvenida_agencia(agencia, user)
        logger.info(f"Welcome email sent to {user.email} for agencia {agencia.nombre}")
        return True
    except Exception as exc:
        logger.error(f"Welcome email task error: {exc}")
        self.retry(exc=exc)


@shared_task(
    bind=True,
    queue="notifications",
    max_retries=3,
    default_retry_delay=10,
    time_limit=120,
    soft_time_limit=100,
)
def notificar_confirmacion_pago_task(self, pago_id):
    from apps.bookings.models import PagoVenta
    from apps.communications.services.notification_dispatcher import notificar_confirmacion_pago

    try:
        pago = PagoVenta.objects.get(pk=pago_id)
        notificar_confirmacion_pago(pago)
        logger.info(f"Payment notification sent for pago {pago_id}")
        return True
    except Exception as exc:
        logger.error(f"Payment notification task error: {exc}")
        self.retry(exc=exc)


@shared_task(
    bind=True,
    queue="notifications",
    max_retries=3,
    default_retry_delay=10,
    time_limit=120,
    soft_time_limit=100,
)
def notificar_recordatorio_pago_task(self, venta_id):
    from apps.bookings.models import Venta
    from apps.communications.services.notification_dispatcher import notificar_recordatorio_pago

    try:
        venta = Venta.objects.get(pk=venta_id)
        notificar_recordatorio_pago(venta)
        logger.info(f"Payment reminder sent for venta {venta_id}")
        return True
    except Exception as exc:
        logger.error(f"Payment reminder task error: {exc}")
        self.retry(exc=exc)


@shared_task(
    bind=True,
    queue="notifications",
    max_retries=3,
    default_retry_delay=10,
    time_limit=120,
    soft_time_limit=100,
)
def notificar_boleto_procesado_task(self, boleto_id):
    from apps.bookings.models import BoletoImportado
    from apps.communications.services.notification_dispatcher import notificar_boleto_procesado

    try:
        boleto = BoletoImportado.objects.get(pk=boleto_id)
        notificar_boleto_procesado(boleto)
        logger.info(f"Ticket processed notification sent for boleto {boleto_id}")
        return True
    except Exception as exc:
        logger.error(f"Ticket processed notification task error: {exc}")
        self.retry(exc=exc)


@shared_task(
    bind=True,
    queue="default",
    max_retries=2,
    default_retry_delay=30,
    time_limit=120,
    soft_time_limit=100,
)
def generate_pdf_task(self, html_content, margins=0.0):
    from apps.common.services.pdf_renderer import PdfRendererService

    try:
        pdf_bytes = PdfRendererService.render_html_to_pdf(html_content, margins)
        logger.info(f"PDF generated: {len(pdf_bytes)} bytes")
        return pdf_bytes
    except Exception as exc:
        logger.error(f"PDF generation task error: {exc}")
        self.retry(exc=exc)


@shared_task(
    bind=True,
    name="core.tasks.backup_database_task",
    max_retries=2,
    default_retry_delay=3600,
    time_limit=600,
    soft_time_limit=540,
)
def backup_database_task(self):
    from django.core.management import call_command

    from core.middleware import system_context

    try:
        with system_context():
            call_command("backup_database", retention_days=7)
            logger.info("Backup diario completado exitosamente")
            return "Backup completado"
    except Exception as exc:
        logger.error(f"Backup diario falló: {exc}")
        self.retry(exc=exc)


@shared_task(
    bind=True,
    queue="notifications",
    max_retries=3,
    default_retry_delay=30,
    time_limit=120,
    soft_time_limit=100,
)
def send_telegram_document_task(self, file_path, caption=None, chat_id=None, agencia_id=None):
    from apps.communications.services.telegram_unified import TelegramNotificationService

    try:
        agencia = None
        if agencia_id:
            from core.models.agencia import Agencia

            agencia = Agencia.objects.get(pk=agencia_id)
        result = TelegramNotificationService.send_document(
            file_path=file_path, caption=caption, chat_id=chat_id, agencia=agencia
        )
        if result:
            logger.info(f"Telegram document sent (file={file_path})")
        else:
            logger.warning(f"Telegram document send returned failure (file={file_path})")
        return result
    except Exception as exc:
        logger.error(f"Telegram document task error: {exc}")
        self.retry(exc=exc)


@shared_task(
    bind=True,
    queue="default",
    max_retries=3,
    default_retry_delay=60,
    time_limit=120,
    soft_time_limit=100,
)
def send_telegram_photo_task(self, agencia_id, filename="logo.png"):
    from apps.communications.services.telegram_unified import upload_logo_to_telegram
    from core.models.agencia import Agencia

    try:
        agencia = Agencia.objects.get(pk=agencia_id)
        branding = agencia.branding
        if not branding or not branding.logo:
            logger.warning(f"Agencia {agencia_id} sin branding o logo")
            return False
        file_id = upload_logo_to_telegram(branding.logo.file, branding.logo.name)
        if file_id:
            branding.logo_telegram_id = file_id
            branding.logo_base64 = None
            branding.save(update_fields=["logo_telegram_id", "logo_base64"])
            logger.info(f"Logo subido a Telegram para agencia {agencia_id}: {file_id}")
        return bool(file_id)
    except Exception as exc:
        logger.error(f"Telegram photo task error for agencia {agencia_id}: {exc}")
        self.retry(exc=exc)


@shared_task(
    bind=True,
    queue="default",
    max_retries=3,
    default_retry_delay=30,
    time_limit=120,
    soft_time_limit=100,
)
def send_factura_to_telegram_task(self, factura_id):
    from apps.finance.models import Factura
    from apps.finance.services.factura_service import FacturaService

    try:
        factura = Factura.objects.get(pk=factura_id)
        result = FacturaService.send_to_telegram_if_needed(factura)
        if result:
            logger.info(f"Factura {factura_id} enviada a Telegram")
        return result
    except Exception as exc:
        logger.error(f"Error sending factura {factura_id} to Telegram: {exc}")
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
    queue="default", max_retries=2, default_retry_delay=5, time_limit=60, soft_time_limit=50
)
@idempotent_task(timeout=3600, key_prefix="celery_binance_order")
def create_binance_order_task(factura_id):
    from celery import current_task
    from django.core.cache import cache

    from apps.finance.models import Factura
    from apps.finance.services.binance_service import BinancePayService

    try:
        factura = Factura.objects.get(pk=factura_id)
        service = BinancePayService()
        pago = service.create_order(factura)
        if pago:
            cache_key = f"binance_order:{factura_id}"
            cache.set(
                cache_key,
                {
                    "prepay_id": pago.prepay_id,
                    "checkout_url": pago.checkout_url,
                    "monto": str(pago.monto),
                    "moneda": pago.moneda,
                    "merchant_trade_no": pago.merchant_trade_no,
                },
                3600,
            )
            logger.info(f"Binance order created for factura {factura_id}: {pago.prepay_id}")
            return {"prepay_id": pago.prepay_id, "checkout_url": pago.checkout_url}
        logger.error(f"Binance order creation failed for factura {factura_id}")
        return None
    except Exception as exc:
        logger.error(f"Binance order task error for factura {factura_id}: {exc}")
        current_task.retry(exc=exc)


@shared_task(
    bind=True,
    queue="notifications",
    max_retries=3,
    default_retry_delay=30,
    time_limit=60,
    soft_time_limit=50,
)
def notify_migration_alert_task(self, check_id):
    from apps.communications.services.notification_dispatcher import notificar_alerta_migratoria
    from core.models.migration_checks import MigrationCheck

    try:
        check = MigrationCheck.objects.get(pk=check_id)
        notificar_alerta_migratoria(check)
        logger.info(f"Migration alert dispatched for check {check_id}")
        return True
    except Exception as exc:
        logger.error(f"Migration alert task error for check {check_id}: {exc}")
        self.retry(exc=exc)


@shared_task(
    bind=True,
    queue="notifications",
    max_retries=2,
    default_retry_delay=10,
    time_limit=30,
    soft_time_limit=20,
)
def answer_telegram_callback_task(self, bot_token, query_id, text):
    import requests

    url = f"https://api.telegram.org/bot{bot_token}/answerCallbackQuery"
    payload = {"callback_query_id": query_id, "text": text, "show_alert": False}
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code != 200:
            logger.error(f"Error en answerCallbackQuery: {response.text}")
        return response.status_code == 200
    except Exception as exc:
        logger.error(f"Error en answerCallbackQuery: {exc}")
        self.retry(exc=exc)


@shared_task(
    bind=True,
    queue="notifications",
    max_retries=2,
    default_retry_delay=10,
    time_limit=30,
    soft_time_limit=20,
)
def edit_telegram_message_task(self, bot_token, chat_id, message_id, text):
    import requests

    url = f"https://api.telegram.org/bot{bot_token}/editMessageText"
    payload = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text,
        "parse_mode": "HTML",
        "reply_markup": {"inline_keyboard": []},
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code != 200:
            logger.error(f"Error en editMessageText: {response.text}")
        return response.status_code == 200
    except Exception as exc:
        logger.error(f"Error en editMessageText: {exc}")
        self.retry(exc=exc)


@shared_task(
    bind=True,
    queue="notifications",
    max_retries=3,
    default_retry_delay=30,
    time_limit=60,
    soft_time_limit=50,
)
def send_evolution_message_task(self, agencia_id, phone_number, text):
    from apps.communications.services.whatsapp_service import WhatsAppEvolutionService

    try:
        service = WhatsAppEvolutionService(agencia_id)
        success = service.send_message(phone_number, text)
        if success:
            logger.info(f"Evolution message sent (agencia={agencia_id}, to={phone_number})")
        else:
            logger.warning(f"Evolution message failed (agencia={agencia_id}, to={phone_number})")
        return success
    except Exception as exc:
        logger.error(f"Evolution message task error: {exc}")
        self.retry(exc=exc)


@shared_task(
    bind=True,
    queue="notifications",
    max_retries=3,
    default_retry_delay=30,
    time_limit=120,
    soft_time_limit=100,
)
def send_evolution_document_task(
    self, agencia_id, phone_number, document_url, filename, caption=""
):
    from apps.communications.services.whatsapp_service import WhatsAppEvolutionService

    try:
        service = WhatsAppEvolutionService(agencia_id)
        success = service.send_document(phone_number, document_url, filename, caption)
        if success:
            logger.info(f"Evolution document sent (agencia={agencia_id}, to={phone_number})")
        else:
            logger.warning(f"Evolution document failed (agencia={agencia_id}, to={phone_number})")
        return success
    except Exception as exc:
        logger.error(f"Evolution document task error: {exc}")
        self.retry(exc=exc)


@shared_task(
    bind=True,
    queue="default",
    max_retries=3,
    default_retry_delay=30,
    time_limit=120,
    soft_time_limit=100,
)
def fetch_unsplash_image_task(self, query):
    import requests

    access_key = os.environ.get("UNSPLASH_ACCESS_KEY")
    if not access_key:
        logger.warning("UNSPLASH_ACCESS_KEY no configurada")
        return None

    try:
        url = "https://api.unsplash.com/search/photos"
        params = {
            "query": f"{query} travel landscape",
            "orientation": "portrait",
            "per_page": 1,
            "client_id": access_key,
        }
        response = requests.get(url, params=params, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data["results"]:
                image_url = data["results"][0]["urls"]["regular"]
                img_response = requests.get(image_url, timeout=10)
                if img_response.status_code == 200:
                    from base64 import b64encode

                    b64_data = b64encode(img_response.content).decode("utf-8")
                    logger.info(f"Unsplash image fetched for query: {query}")
                    return {
                        "base64": b64_data,
                        "content_type": img_response.headers.get("Content-Type", "image/jpeg"),
                    }
        logger.warning(f"No Unsplash results for query: {query}")
        return None
    except Exception as exc:
        logger.error(f"Unsplash fetch error for query {query}: {exc}")
        self.retry(exc=exc)


@shared_task(
    bind=True,
    queue="default",
    max_retries=2,
    default_retry_delay=10,
    time_limit=30,
    soft_time_limit=20,
)
def fetch_airline_logo_task(self, airline_name):
    import json

    import requests
    from django.conf import settings

    try:
        json_path = os.path.join(settings.BASE_DIR, "core", "data", "airlines.json")
        if not os.path.exists(json_path):
            return None

        with open(json_path, encoding="utf-8") as f:
            airlines_data = json.load(f)

        iata_code = None
        airline_name_lower = airline_name.lower().strip()

        for item in airlines_data:
            if airline_name_lower == item["name"].lower():
                iata_code = item["code"]
                break
            elif airline_name_lower in item["name"].lower():
                if not iata_code:
                    iata_code = item["code"]

        if not iata_code and len(airline_name) == 2:
            iata_code = airline_name.upper()

        if not iata_code:
            return None

        logo_url = f"https://pics.avs.io/200/200/{iata_code}.png"
        response = requests.get(logo_url, timeout=5)
        if response.status_code == 200:
            from base64 import b64encode

            b64_data = b64encode(response.content).decode("utf-8")
            logger.info(f"Airline logo fetched: {airline_name} ({iata_code})")
            return {"base64": b64_data, "content_type": "image/png"}
        return None
    except Exception as exc:
        logger.error(f"Airline logo fetch error for {airline_name}: {exc}")
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
    queue="notifications",
    max_retries=3,
    default_retry_delay=30,
    time_limit=60,
    soft_time_limit=50,
)
def get_telegram_file_url_task(self, file_id, agencia_id=None):
    from apps.communications.services.telegram_unified import TelegramNotificationService

    try:
        agencia = None
        if agencia_id:
            from core.models.agencia import Agencia

            agencia = Agencia.objects.get(pk=agencia_id)
        url = TelegramNotificationService.get_file_url(file_id, agencia=agencia)
        logger.info(f"Telegram file URL resolved for file_id={file_id}")
        return url
    except Exception as exc:
        logger.error(f"Telegram file URL task error: {exc}")
        self.retry(exc=exc)


@shared_task(
    bind=True,
    queue="notifications",
    max_retries=3,
    default_retry_delay=30,
    time_limit=60,
    soft_time_limit=50,
)
def fetch_bcv_rates_task(self):
    from apps.finance.services.bcv_scraper import obtener_tasas_bcv

    try:
        tasas = obtener_tasas_bcv()
        if tasas:
            logger.info(f"BCV rates fetched: {list(tasas.keys())}")
        else:
            logger.warning("No BCV rates fetched")
        return {k: str(v) for k, v in tasas.items()} if tasas else None
    except Exception as exc:
        logger.error(f"BCV rates fetch error: {exc}")
        self.retry(exc=exc)


@shared_task(
    bind=True,
    queue="default",
    max_retries=3,
    default_retry_delay=30,
    time_limit=60,
    soft_time_limit=50,
)
def fetch_tasas_venezuela_task(self):
    from apps.contabilidad.tasas_venezuela_client import TasasVenezuelaClient

    try:
        tasas = TasasVenezuelaClient.obtener_todas_tasas()
        if tasas:
            logger.info(f"Venezuela rates fetched: {len(tasas)} sources")
        else:
            logger.warning("No Venezuela rates fetched")
        return tasas
    except Exception as exc:
        logger.error(f"Venezuela rates fetch error: {exc}")
        self.retry(exc=exc)


@shared_task(
    bind=True,
    queue="default",
    max_retries=3,
    default_retry_delay=30,
    time_limit=60,
    soft_time_limit=50,
)
def fetch_image_base64_task(self, image_source):
    from apps.common.utils.images import get_image_as_base64

    try:
        result = get_image_as_base64(image_source)
        if result:
            logger.info(f"Image fetched as base64 from: {str(image_source)[:80]}")
        else:
            logger.warning(f"Image fetch returned None: {str(image_source)[:80]}")
        return result
    except Exception as exc:
        logger.error(f"Image base64 fetch error: {exc}")
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


@shared_task(queue="default", time_limit=120, soft_time_limit=100)
def fetch_all_qr_codes_task():
    """Renueva el QR de WhatsApp para todas las agencias con Evolution configurado.

    Se ejecuta periódicamente por Celery Beat. Por cada agencia activa con un
    subdominio_slug configurado, dispara fetch_evolution_qr_task en paralelo.
    Solo dispara fetch si la instancia NO está ya conectada.
    """
    from core.models.agencia import Agencia

    # subdominio_slug vive en AgenciaConfiguracion, usamos el ORM correcto
    agencias = (
        Agencia.objects.filter(activa=True)
        .select_related("configuracion")
        .filter(configuracion__subdominio_slug__isnull=False)
        .exclude(configuracion__subdominio_slug="")
    )
    total = 0
    for ag in agencias:
        slug = ag.subdominio_slug
        if slug:
            fetch_evolution_qr_task.delay(slug)
            total += 1

    logger.info(f"fetch_all_qr_codes_task: despachadas {total} tareas de QR para agencias activas.")
    return total


@shared_task(
    bind=True,
    queue="default",
    max_retries=2,
    default_retry_delay=5,
    time_limit=60,
    soft_time_limit=50,
)
def fetch_evolution_qr_task(self, instance_name):
    """Fetch QR code for an Evolution instance and cache it.

    This task retrieves the QR (base64) from the Evolution API via HTTP and stores
    it in Redis for 2 minutes. It replaces the previous incorrectly‑bound task
    definition that prevented execution.
    """
    import json

    import requests
    from django.core.cache import cache

    from apps.communications.services.evolution_api_service import EvolutionService

    cache_key = f"evo_qr:{instance_name}"

    # 1. Si ya está conectado, no necesitamos el QR y evitamos tocar la API de conexión
    if EvolutionService.get_connection_status(instance_name):
        logger.info(f"Instancia '{instance_name}' ya está conectada. Omitiendo fetch de QR.")
        cache.delete(cache_key)
        return None

    try:
        base_url = EvolutionService._get_base_url()
        headers = EvolutionService._get_headers()
        # The GET endpoint does not expect a JSON payload, so drop the Content-Type header.
        headers.pop("Content-Type", None)
        response = requests.get(
            f"{base_url}/instance/connect/{instance_name}", headers=headers, timeout=15
        )
        if response.status_code == 404:
            logger.info(f"Instance '{instance_name}' not found. Attempting to create...")
            EvolutionService.create_instance(instance_name)
            response = requests.get(
                f"{base_url}/instance/connect/{instance_name}", headers=headers, timeout=15
            )
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, dict) and data.get("base64"):
                cache.set(cache_key, data["base64"], 300)  # 5 minutos
                logger.info(f"Evolution QR cached via HTTP for {instance_name}")
                return data["base64"]
    except (requests.RequestException, json.JSONDecodeError, ValueError) as e:
        logger.error(f"Failed to fetch Evolution QR for {instance_name}: {e}")
        return None

    try:
        import websocket

        ws_url = base_url.replace("http://", "ws://")
        ws_url = f"{ws_url}/{instance_name}"
        ws_headers = {"apikey": headers.get("apikey", "")}

        ws = websocket.create_connection(ws_url, header=ws_headers, timeout=2)
        for _ in range(10):
            try:
                message = ws.recv()
                data = json.loads(message)
                event = data.get("event", "")
                qr = data.get("qrcode", data if event else {})
                if isinstance(qr, dict) and qr.get("base64"):
                    cache.set(cache_key, qr["base64"], 120)
                    logger.info(f"Evolution QR cached via WebSocket for {instance_name}")
                    ws.close()
                    return qr["base64"]
            except (json.JSONDecodeError, KeyError, ValueError):
                continue
        ws.close()
    except ImportError:
        logger.warning("websocket module not available for QR fetch")
    return None


@shared_task(queue="default", time_limit=120, soft_time_limit=100)
def process_scheduled_whatsapp_messages():
    """Envía los mensajes de WhatsApp programados cuya hora ya llegó.

    Se ejecuta cada minuto vía Celery Beat. Busca mensajes en estado
    'scheduled' con programado_para <= ahora y los envía.
    """
    from django.utils import timezone

    from apps.crm.models import WhatsAppScheduledMessage

    now = timezone.now()
    pendientes = WhatsAppScheduledMessage.objects.filter(
        estado="scheduled", programado_para__lte=now
    ).select_related("agencia", "cliente")

    enviados = 0
    for msg in pendientes:
        msg.estado = "sending"
        msg.save(update_fields=["estado"])

        try:
            instance_name = f"agencia_{msg.agencia_id}"
            if msg.agencia and hasattr(msg.agencia, "configuracion"):
                cfg = msg.agencia.configuracion
                if cfg.evolution_instance_name:
                    instance_name = cfg.evolution_instance_name

            from apps.communications.services.evolution_api_service import EvolutionService

            exito = EvolutionService.send_text(instance_name, msg.telefono, msg.texto)

            if exito:
                from apps.crm.models import MensajeWhatsApp

                m = MensajeWhatsApp.objects.create(
                    cliente=msg.cliente,
                    direccion="OUT",
                    texto=msg.texto,
                    estado="sent",
                    tipo_mensaje="text",
                    agencia=msg.agencia,
                )
                msg.mensaje_resultante = m
                msg.estado = "sent"
                msg.save(update_fields=["estado", "mensaje_resultante"])
                enviados += 1
            else:
                msg.estado = "failed"
                msg.error_msg = "Error al enviar vía Evolution"
                msg.save(update_fields=["estado", "error_msg"])
        except Exception as e:
            msg.estado = "failed"
            msg.error_msg = str(e)[:500]
            msg.save(update_fields=["estado", "error_msg"])
            logger.error(f"Error enviando WA programado #{msg.pk}: {e}")

    if pendientes:
        logger.info(f"Mensajes WA programados procesados: {enviados}/{len(pendientes)} enviados")
    return enviados


@shared_task(
    name="core.tasks.limpiar_axes_logs",
    time_limit=300,
    soft_time_limit=270,
    max_retries=2,
    default_retry_delay=60,
)
def limpiar_axes_logs():
    try:
        from datetime import timedelta

        from axes.models import AccessAttempt, AccessFailureLog
        from django.utils import timezone

        cutoff = timezone.now() - timedelta(days=30)
        AccessAttempt.objects.filter(attempt_time__lt=cutoff).delete()
        AccessFailureLog.objects.filter(attempt_time__lt=cutoff).delete()
        return "Axes logs limpiados con éxito"
    except Exception as e:
        logger.error(f"Error limpiando logs Axes: {e}")
        return f"Error limpiando logs Axes: {e}"


@shared_task(
    name="core.tasks.limpiar_sesiones_expiradas",
    time_limit=300,
    soft_time_limit=270,
    max_retries=2,
    default_retry_delay=60,
)
def limpiar_sesiones_expiradas():
    try:
        from django.contrib.sessions.models import Session
        from django.utils import timezone

        Session.objects.filter(expire_date__lt=timezone.now()).delete()
        return "Sesiones expiradas limpiadas con exito"
    except Exception as e:
        logger.error(f"Error limpiando sesiones: {e}")
        return f"Error limpiando sesiones: {e}"


@shared_task(queue="notifications", max_retries=3, default_retry_delay=30, time_limit=60)
def send_telegram_to_client_task(
    cliente_id, message, parse_mode="HTML", document_url=None, caption=None
):
    """Envía un mensaje de Telegram a un cliente."""
    from apps.communications.services.telegram_unified import send_telegram_to_client
    from apps.crm.models import Cliente

    try:
        cliente = Cliente.objects.get(pk=cliente_id)
        success = send_telegram_to_client(cliente, message, parse_mode, document_url, caption)
        logger.info(
            f"Telegram to client {cliente_id}: {'OK' if success else 'FAILED (no chat_id)'}"
        )
        return success
    except Cliente.DoesNotExist:
        logger.error(f"Cliente {cliente_id} no encontrado")
        return False


@shared_task(queue="notifications", max_retries=3, default_retry_delay=30, time_limit=60)
def notify_cliente_confirmacion_venta_task(venta_id):
    """Envía confirmación de venta al cliente por Telegram."""
    from apps.communications.services.telegram_unified import notify_cliente_confirmacion_venta
    from apps.sales.models import Venta

    try:
        venta = Venta.objects.select_related("cliente").get(pk=venta_id)
        return notify_cliente_confirmacion_venta(venta.cliente, venta)
    except Exception as e:
        logger.error(f"Error notificando venta {venta_id} por Telegram: {e}")
        return False


@shared_task(queue="notifications", max_retries=3, default_retry_delay=30, time_limit=60)
def notify_cliente_recordatorio_pago_task(venta_id):
    """Envía recordatorio de pago al cliente por Telegram."""
    from apps.communications.services.telegram_unified import notify_cliente_recordatorio_pago
    from apps.sales.models import Venta

    try:
        venta = Venta.objects.select_related("cliente").get(pk=venta_id)
        return notify_cliente_recordatorio_pago(venta.cliente, venta)
    except Exception as e:
        logger.error(f"Error notificando recordatorio {venta_id} por Telegram: {e}")
        return False


@shared_task(queue="notifications", max_retries=3, default_retry_delay=30, time_limit=60)
def notify_cliente_alerta_migratoria_task(cliente_id, destino, requisitos):
    """Envía alerta migratoria al cliente por Telegram."""
    from apps.communications.services.telegram_unified import notify_cliente_alerta_migratoria
    from apps.crm.models import Cliente

    try:
        cliente = Cliente.objects.get(pk=cliente_id)
        return notify_cliente_alerta_migratoria(cliente, destino, requisitos)
    except Exception as e:
        logger.error(f"Error notificando alerta migratoria a cliente {cliente_id}: {e}")
        return False


@shared_task(
    name="core.tasks.limpiar_celery_results",
    time_limit=300,
    soft_time_limit=270,
    max_retries=2,
    default_retry_delay=60,
)
def limpiar_celery_results(days=30):
    try:
        from django.utils import timezone
        from django_celery_results.models import TaskResult

        cutoff = timezone.now() - datetime.timedelta(days=days)
        count, _ = TaskResult.objects.filter(date_done__lt=cutoff).delete()
        result = f"Celery results limpiados: {count} registros eliminados (>{days} dias)"
        logger.info(result)
        return result
    except Exception as e:
        logger.error(f"Error limpiando celery results: {e}")
        return f"Error limpiando celery results: {e}"

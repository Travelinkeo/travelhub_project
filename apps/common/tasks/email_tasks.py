import base64
import logging
from email.header import decode_header
from io import BytesIO

from celery import shared_task

from apps.common.utils.celery_utils import tenant_task

logger = logging.getLogger(__name__)


def get_filename_from_header(header):
    """get_filename_from_header."""
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
    """procesar_correo_individual_agencia."""
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
            logger.info(f" Procesando agencia SaaS (individual): {agencia.nombre} ({email_user})")

            monitor = EmailMonitorService(
                agencia=agencia, notification_type="telegram", process_all=False, mark_as_read=True
            )

            cantidad = monitor.procesar_una_vez()

            if cantidad and cantidad > 0:
                canal = getattr(config, "canal_notificaciones_mailbot", "telegram")
                _notificar_operador(agencia, cantidad, canal)

            return f"Agencia {agencia.nombre} procesada con éxito. {cantidad} correos procesados."
    except Exception as e:
        logger.error(f" Error procesando agencia {agencia_id} en paralelo: {e}")
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
        logger.info(f" Telegram de monitoreo enviado a operador de {agencia.nombre}")
    except Exception as e:
        logger.warning(f" No se pudo enviar Telegram al operador de {agencia.nombre}: {e}")


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
        logger.info(f" WhatsApp de monitoreo enviado a operador de {agencia.nombre}")
    except Exception as e:
        logger.warning(f" No se pudo enviar WhatsApp al operador de {agencia.nombre}: {e}")


@shared_task(
    name="core.tasks.process_incoming_emails",
    time_limit=600,
    soft_time_limit=540,
    max_retries=3,
    default_retry_delay=300,
    acks_late=True,
)
def process_incoming_emails():
    """process_incoming_emails."""
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
    name="core.tasks.migrar_logos_agencia_task",
    time_limit=600,
    soft_time_limit=540,
    max_retries=2,
    default_retry_delay=600,
)
def migrar_logos_agencia_task(agencia_id, **kwargs):
    """migrar_logos_agencia_task."""
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
    bind=True,
    queue="notifications",
    max_retries=3,
    default_retry_delay=10,
    time_limit=60,
    soft_time_limit=50,
)
def send_email_task(self, recipient, subject, message, from_email=None, agencia_id=None, **kwargs):
    """send_email_task."""
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
def notify_migration_alert_task(self, check_id):
    """notify_migration_alert_task."""
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

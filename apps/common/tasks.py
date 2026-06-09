import logging
import os
import base64
import datetime
from io import BytesIO
from email.header import decode_header
from celery import shared_task
from django.conf import settings
from apps.common.utils.celery_utils import tenant_task

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
        if not config or not config.correo_emisiones or not config.password_app_correo:
            return f"Agencia {agencia_id} no configurada."

        with agency_context(agencia):
            logger.info(
                f"🔄 Procesando agencia SaaS (individual): {agencia.nombre} ({config.correo_emisiones})"
            )

            monitor = EmailMonitorService(
                agencia=agencia, notification_type="telegram", process_all=False, mark_as_read=True
            )

            cantidad = monitor.procesar_una_vez()
            return f"Agencia {agencia.nombre} procesada con éxito. {cantidad} correos procesados."
    except Exception as e:
        logger.error(f"❌ Error procesando agencia {agencia_id} en paralelo: {e}")
        raise


@shared_task(
    name="core.tasks.process_incoming_emails",
    time_limit=600,
    soft_time_limit=540,
    max_retries=3,
    default_retry_delay=300,
    acks_late=True,
)
def process_incoming_emails():
    from core.models.agencia import Agencia

    logger.info(
        "🚀 Iniciando tarea programada: Procesamiento de Correos (Multi-Tenant, Paralelizado)"
    )

    agencias_qs = (
        Agencia.objects.filter(activa=True)
        .exclude(configuracion__correo_emisiones__isnull=True)
        .exclude(configuracion__correo_emisiones__exact="")
    )

    if not agencias_qs.exists():
        logger.warning("No hay agencias activas para monitorear.")
        return "Sin agencias activas."

    total_agencias = 0
    for agencia in agencias_qs.iterator(chunk_size=50):
        config = agencia.configuracion
        if not config or not config.correo_emisiones or not config.password_app_correo:
            continue

        procesar_correo_individual_agencia.delay(agencia.id)
        total_agencias += 1

    resultado = (
        f"Se despacharon tareas de procesamiento en paralelo para {total_agencias} agencias."
    )
    logger.info(resultado)
    return resultado


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
    bind=True, max_retries=2, default_retry_delay=3600, time_limit=600, soft_time_limit=540
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
        raise self.retry(exc=exc) from exc

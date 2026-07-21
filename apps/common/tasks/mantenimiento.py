import datetime
import logging
import os

from celery import shared_task

logger = logging.getLogger(__name__)


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

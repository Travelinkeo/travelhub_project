"""Tareas asíncronas (Celery) para la aplicación reports.
"""

import logging
from datetime import date, timedelta

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    queue="celery",
    max_retries=2,
    default_retry_delay=60,
    time_limit=300,
    soft_time_limit=240,
)
def enviar_reportes_programados_task(self):
    # enviar_reportes_programados_task: Envía ar reportes programados task. Args: datos del mensaje. Returns: resultado del envío.
    from django.utils import timezone

    from .models import ReporteProgramado

    now = timezone.now()
    hoy = now.date()
    reportes_enviados = 0

    reportes = ReporteProgramado.objects.filter(activo=True).select_related("agencia")

    for reporte in reportes:
        try:
            if not _debe_enviarse(reporte, hoy):
                continue

            csv_content = _generar_csv_reporte(reporte)
            if not csv_content:
                logger.warning("Reporte %s generó CSV vacío, se omite", reporte.nombre)
                continue

            _enviar_por_email(reporte, csv_content)

            reporte.ultimo_envio = now
            reporte.save(update_fields=["ultimo_envio"])
            reportes_enviados += 1

        except Exception as e:
            logger.error("Error enviando reporte %s: %s", reporte.nombre, e)
            continue

    logger.info("Reportes programados: %d enviados de %d revisados", reportes_enviados, reportes.count())
    return reportes_enviados


def _debe_enviarse(reporte, hoy):
    # _debe_enviarse:  debe enviarse. Args: según implementación. Returns: según implementación.
    if not reporte.ultimo_envio:
        return True

    ultimo = reporte.ultimo_envio.date()
    freq = reporte.frecuencia

    if freq == "diario":
        return ultimo < hoy
    elif freq == "semanal":
        dia_semana = reporte.dia_semana or hoy.isoweekday()
        if hoy.isoweekday() != dia_semana:
            return False
        return ultimo < hoy - timedelta(days=6)
    elif freq == "mensual":
        return ultimo.month < hoy.month or ultimo.year < hoy.year
    elif freq == "trimestral":
        trim_actual = (hoy.month - 1) // 3
        trim_ultimo = (ultimo.month - 1) // 3
        return trim_actual != trim_ultimo or ultimo.year < hoy.year
    elif freq == "anual":
        return ultimo.year < hoy.year

    return False


def _generar_csv_reporte(reporte):
    # _generar_csv_reporte:  generar csv reporte. Args: según implementación. Returns: según implementación.
    from .services.kpi_metrics import KPIMetrics
    from .services.report_exporter import exportar_csv

    agencia = reporte.agencia
    metrics = KPIMetrics(agencia)
    return exportar_csv(metrics)


def _enviar_por_email(reporte, csv_content):
    # _enviar_por_email:  enviar por email. Args: según implementación. Returns: según implementación.
    if not reporte.destinatarios:
        return

    from django.core.mail import EmailMultiAlternatives
    from django.conf import settings

    agencia = reporte.agencia
    subject = f"Reporte KPI: {reporte.nombre} - {agencia.nombre}"
    text_body = (
        f"Adjunto encontrará el reporte KPI programado: {reporte.nombre}\n"
        f"Agencia: {agencia.nombre}\n"
        f"Tipo: {reporte.get_tipo_display()}\n"
        f"Frecuencia: {reporte.get_frecuencia_display()}\n"
        f"---\n"
        f"TravelHub - Reportes Automáticos"
    )

    sender = agencia.email_principal or settings.DEFAULT_FROM_EMAIL

    for destinatario in reporte.destinatarios:
        try:
            email = EmailMultiAlternatives(
                subject, text_body, sender, [destinatario.strip()]
            )
            email.attach(
                f"reporte_{reporte.nombre.lower().replace(' ', '_')}.csv",
                csv_content,
                "text/csv",
            )
            email.send(fail_silently=False)
        except Exception as e:
            logger.error("Error enviando reporte %s a %s: %s", reporte.nombre, destinatario, e)

    logger.info("Reporte %s enviado a %d destinatarios", reporte.nombre, len(reporte.destinatarios))

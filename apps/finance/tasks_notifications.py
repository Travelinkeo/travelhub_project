import logging

from celery import shared_task
from django.contrib.auth import get_user_model
from django.db.models import Count, Q

from apps.communications.services.notification_dispatcher import NotificationService
from apps.finance.models_stubs import ReporteReconciliacion
from apps.finance.services.pdf_service import PDFService

logger = logging.getLogger(__name__)
User = get_user_model()


@shared_task(
    bind=True,
    name="finance.enviar_reporte_gerencia_task",
    queue="notifications",
    max_retries=3,
    default_retry_delay=60 * 5,
    time_limit=300,
    soft_time_limit=270,
)
def enviar_reporte_gerencia_task(self, reporte_id, user_id, email_destino, agencia_id=None):
    from core.api import Agencia, agency_context, system_context

    try:
        if agencia_id:
            agencia = Agencia.objects.get(pk=agencia_id)
            ctx = agency_context(agencia)
        else:
            ctx = system_context()

        with ctx:
            reporte = ReporteReconciliacion.objects.get(pk=reporte_id)
            user = User.objects.get(pk=user_id)

            stats = reporte.conciliaciones.aggregate(
                total=Count("id_conciliacion"),
                matches=Count("id_conciliacion", filter=Q(estado="OK")),
                discrepancias=Count("id_conciliacion", filter=Q(estado="DISCREPANCIA")),
            )

            pdf_bytes = PDFService.generate_reconciliation_report(reporte_id, user)

            NotificationService.enviar_reporte_pdf_email(
                agencia=user.agencia, email_destino=email_destino, pdf_bytes=pdf_bytes, kpis=stats
            )

            logger.info(f"📬 Reporte de Recon. {reporte_id} enviado exitosamente a {email_destino}")
            return f"Enviado a {email_destino}"

    except Exception as exc:
        logger.error(f"❌ Fallo enviando reporte {reporte_id} a {email_destino}: {exc}")
        raise self.retry(exc=exc) from exc

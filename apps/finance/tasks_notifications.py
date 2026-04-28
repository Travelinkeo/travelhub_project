import logging
from celery import shared_task
from django.contrib.auth import get_user_model
from apps.finance.models.reconciliacion import ReporteReconciliacion
from apps.finance.services.pdf_service import PDFService
from core.services.notification_service import NotificationService
from django.db.models import Count, Sum, Q

logger = logging.getLogger(__name__)
User = get_user_model()

@shared_task(
    bind=True,
    name='finance.enviar_reporte_gerencia_task',
    queue='notifications',
    max_retries=3,
    default_retry_delay=60 * 5  # 5 minutos
)
def enviar_reporte_gerencia_task(self, reporte_id, user_id, email_destino):
    """
    Tarea Asíncrona: Orquesta la generación del PDF y su envío por correo.
    """
    try:
        reporte = ReporteReconciliacion.objects.get(pk=reporte_id)
        user = User.objects.get(pk=user_id)
        
        # 1. Generar los KPIs en caliente para el cuerpo del correo
        stats = reporte.conciliaciones.aggregate(
            total=Count('id_conciliacion'),
            matches=Count('id_conciliacion', filter=Q(estado='OK')),
            discrepancias=Count('id_conciliacion', filter=Q(estado='DISCREPANCIA'))
        )

        # 2. Generar el PDF (en memoria)
        pdf_bytes = PDFService.generate_reconciliation_report(reporte_id, user)

        # 3. Enviar el correo con adjunto
        NotificationService.enviar_reporte_pdf_email(
            agencia=user.agencia,
            email_destino=email_destino,
            pdf_bytes=pdf_bytes,
            kpis=stats
        )

        logger.info(f"📬 Reporte de Recon. {reporte_id} enviado exitosamente a {email_destino}")
        return f"Enviado a {email_destino}"

    except Exception as exc:
        logger.error(f"❌ Fallo enviando reporte {reporte_id} a {email_destino}: {exc}")
        # Reintento exponencial por si el servidor de correo tiene un timeout momentáneo
        raise self.retry(exc=exc)

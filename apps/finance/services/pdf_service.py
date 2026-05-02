import logging
import io
from django.template.loader import render_to_string

def _get_html_renderer():
    """Lazy loader for WeasyPrint HTML to avoid boot-time hangs."""
    try:
        from weasyprint import HTML
        return HTML
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Failed to import WeasyPrint: {e}")
        return None

from django.utils import timezone
from django.db.models import Count, Sum, Q
from apps.finance.models.reconciliacion import ReporteReconciliacion

logger = logging.getLogger(__name__)

class PDFService:
    """
    SERVICIO DE RENDERIZADO PDF (WEASYPRINT ENGINE):
    Genera reportes de gestión profesional en memoria para evitar I/O innecesario.
    """

    @staticmethod
    def generate_reconciliation_report(reporte_id, user) -> io.BytesIO:
        """
        Genera el PDF consolidado para un reporte de conciliación específico.
        """
        try:
            reporte = ReporteReconciliacion.objects.get(pk=reporte_id)
            
            # 1. Preparar Contexto de Negocio
            stats = reporte.conciliaciones.aggregate(
                total=Count('id_conciliacion'),
                matches=Count('id_conciliacion', filter=Q(estado='OK')),
                discrepancias=Count('id_conciliacion', filter=Q(estado='DISCREPANCIA')),
                monto_ajuste=Sum('diferencia_total')
            )

            context = {
                'reporte': reporte,
                'agencia': user.agencia,
                'user': user,
                'kpis': stats,
                'conciliaciones': reporte.conciliaciones.select_related('linea_reporte', 'boleto_local', 'sugerencia_asiento'),
                'fecha_generacion': timezone.now()
            }

            # 2. Renderizar Template a HTML
            html_string = render_to_string('finance/reports/reconciliation_pdf.html', context)

            # 3. Convertir a PDF usando WeasyPrint (en memoria)
            HTML_renderer = _get_html_renderer()
            if not HTML_renderer:
                raise Exception("WeasyPrint is not available.")

            pdf_file = io.BytesIO()
            HTML_renderer(string=html_string).write_pdf(target=pdf_file)
            pdf_file.seek(0)

            logger.info(f"📄 Reporte PDF generado para la Conciliación {reporte_id} de {user.agencia.nombre}")
            return pdf_file

        except Exception as e:
            logger.exception(f"Falla crítica generando reporte PDF: {e}")
            raise e

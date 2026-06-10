from datetime import datetime

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.views import View

from apps.common.services.reports.excel_generator import ExcelGenerator
from apps.common.services.reports.report_data_aggregator import ReportDataAggregator
from core.middleware import get_current_agency


class ExportReportView(LoginRequiredMixin, View):
    """View to handle report export requests. Supports Excel format initially."""

    def get(self, request, *args, **kwargs):
        report_type = request.GET.get("report_type", "ventas_generales")
        file_format = request.GET.get("format", "excel")
        start_date_str = request.GET.get("start_date")
        end_date_str = request.GET.get("end_date")

        start_date = None
        end_date = None
        if start_date_str:
            try:
                start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            except ValueError:
                pass
        if end_date_str:
            try:
                end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
            except ValueError:
                pass

        agencia = get_current_agency()

        if report_type == "ventas_generales":
            headers, data = ReportDataAggregator.get_general_sales_data(
                start_date, end_date, agencia=agencia
            )
            filename_prefix = "Ventas_Generales"
        else:
            # Fallback or error
            return HttpResponse("Tipo de reporte no válido.", status=400)

        # Generate File
        if file_format == "excel":
            generator = ExcelGenerator(headers, data, sheet_name=filename_prefix)
            file_buffer = generator.generate()

            # Prepare Response
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{filename_prefix}_{timestamp}.xlsx"

            response = HttpResponse(
                file_buffer.getvalue(),
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
            response["Content-Disposition"] = f'attachment; filename="{filename}"'
            return response

        else:
            return HttpResponse("Formato no soportado.", status=400)

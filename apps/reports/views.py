import json
import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.views import View

from core.security import get_agencia_from_request

from .services.chart_data import (
    boletos_por_aerolinea_chart,
    resumen_cards,
    ventas_diarias_chart,
    ventas_por_vendedor_chart,
)
from .services.kpi_metrics import KPIMetrics
from .services.report_exporter import exportar_csv

logger = logging.getLogger(__name__)


class KpiDashboardView(LoginRequiredMixin, View):
    """Dashboard principal de KPIs con cards y gráficos."""

    template_name = "reports/dashboard.html"

    def get(self, request):
        agencia = get_agencia_from_request(request)
        if not agencia:
            return render(request, self.template_name, {"sin_agencia": True})

        metrics = KPIMetrics(agencia)

        ctx = {
            "cards": resumen_cards(metrics),
            "chart_ventas_diarias": json.dumps(ventas_diarias_chart(metrics)),
            "chart_ventas_vendedor": json.dumps(ventas_por_vendedor_chart(metrics)),
            "chart_boletos_aerolinea": json.dumps(boletos_por_aerolinea_chart(metrics)),
            "resumen": metrics.resumen(),
            "current_agency": agencia,
        }
        return render(request, self.template_name, ctx)


class KpiChartDataView(LoginRequiredMixin, View):
    """Endpoint JSON para recargar gráficos vía HTMX/JS."""

    def get(self, request):
        agencia = get_agencia_from_request(request)
        if not agencia:
            return JsonResponse({"error": "No agency"}, status=400)

        metrics = KPIMetrics(agencia)
        chart_type = request.GET.get("chart", "ventas_diarias")

        charts = {
            "ventas_diarias": ventas_diarias_chart(metrics),
            "ventas_vendedor": ventas_por_vendedor_chart(metrics),
            "boletos_aerolinea": boletos_por_aerolinea_chart(metrics),
        }
        return JsonResponse(charts.get(chart_type, charts["ventas_diarias"]))


class KpiExportView(LoginRequiredMixin, View):
    """Exporta KPIs a CSV."""

    def get(self, request):
        agencia = get_agencia_from_request(request)
        if not agencia:
            return HttpResponse("No agency", status=400)

        metrics = KPIMetrics(agencia)
        csv_content = exportar_csv(metrics)

        response = HttpResponse(csv_content, content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = 'attachment; filename="kpi_report.csv"'
        return response

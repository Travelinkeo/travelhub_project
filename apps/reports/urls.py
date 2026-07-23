from django.urls import path

from . import views

app_name = "reports"

urlpatterns = [
    path("", views.KpiDashboardView.as_view(), name="kpi_dashboard"),
    path("chart-data/", views.KpiChartDataView.as_view(), name="kpi_chart_data"),
    path("export/csv/", views.KpiExportView.as_view(), name="kpi_export"),
]

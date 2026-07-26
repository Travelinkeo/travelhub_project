from django.contrib import admin

from core.api import SaaSAdminMixin

from .models import KpiSnapshot, ReporteKPI, ReporteProgramado


@admin.register(ReporteKPI)
class ReporteKPIAdmin(SaaSAdminMixin, admin.ModelAdmin):
    """ReporteKPIAdmin."""

    list_display = ["nombre", "tipo", "periodo", "activo"]
    list_filter = ["tipo", "periodo", "activo"]


@admin.register(KpiSnapshot)
class KpiSnapshotAdmin(SaaSAdminMixin, admin.ModelAdmin):
    """KpiSnapshotAdmin."""

    list_display = ["metrica", "valor", "fecha", "agencia"]
    list_filter = ["metrica", "fecha"]
    date_hierarchy = "fecha"


@admin.register(ReporteProgramado)
class ReporteProgramadoAdmin(SaaSAdminMixin, admin.ModelAdmin):
    """ReporteProgramadoAdmin."""

    list_display = ["nombre", "tipo", "frecuencia", "activo"]
    list_filter = ["tipo", "frecuencia", "activo"]

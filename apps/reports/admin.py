from django.contrib import admin

from .models import KpiSnapshot, ReporteKPI, ReporteProgramado


@admin.register(ReporteKPI)
class ReporteKPIAdmin(admin.ModelAdmin):
    list_display = ["nombre", "tipo", "periodo", "activo"]
    list_filter = ["tipo", "periodo", "activo"]


@admin.register(KpiSnapshot)
class KpiSnapshotAdmin(admin.ModelAdmin):
    list_display = ["metrica", "valor", "fecha", "agencia"]
    list_filter = ["metrica", "fecha"]
    date_hierarchy = "fecha"


@admin.register(ReporteProgramado)
class ReporteProgramadoAdmin(admin.ModelAdmin):
    list_display = ["nombre", "tipo", "frecuencia", "activo"]
    list_filter = ["tipo", "frecuencia", "activo"]

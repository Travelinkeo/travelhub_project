"""Configuración del panel de administración para reports.
"""

from django.contrib import admin

from core.api import SaaSAdminMixin

from .models import KpiSnapshot, ReporteKPI, ReporteProgramado


@admin.register(ReporteKPI)
class ReporteKPIAdmin:
    """Configuración de administración para reportekpi. Uso: instanciar según necesidad del dominio.
    """
    list_display = ["nombre", "tipo", "periodo", "activo"]
    list_filter = ["tipo", "periodo", "activo"]


@admin.register(KpiSnapshot)
class KpiSnapshotAdmin:
    """Configuración de administración para kpisnapshot. Uso: instanciar según necesidad del dominio.
    """
    list_display = ["metrica", "valor", "fecha", "agencia"]
    list_filter = ["metrica", "fecha"]
    date_hierarchy = "fecha"


@admin.register(ReporteProgramado)
class ReporteProgramadoAdmin:
    """Configuración de administración para reporteprogramado. Uso: instanciar según necesidad del dominio.
    """
    list_display = ["nombre", "tipo", "frecuencia", "activo"]
    list_filter = ["tipo", "frecuencia", "activo"]

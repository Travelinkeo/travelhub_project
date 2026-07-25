"""Configuración de la aplicación Django reports.
"""

from django.apps import AppConfig


class ReportsConfig:
    """Configuración de reports. Uso: instanciar según necesidad del dominio.
    """
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.reports"
    verbose_name = "Reportes KPI"

"""Modelos de base de datos para la aplicación reports.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _

from core.models.base import AgenciaMixin


class ReporteKPI:
    """Clase ReporteKPI. Uso: según contexto de la aplicación.
    """
    TIPOS = [
        ("ventas", _("Ventas")),
        ("rentabilidad", _("Rentabilidad")),
        ("tickets", _("Tickets/Boletos")),
        ("clientes", _("Clientes")),
        ("comisiones", _("Comisiones")),
        ("general", _("General")),
    ]

    PERIODOS = [
        ("diario", _("Diario")),
        ("semanal", _("Semanal")),
        ("mensual", _("Mensual")),
        ("trimestral", _("Trimestral")),
        ("anual", _("Anual")),
    ]

    nombre = models.CharField(max_length=120)
    tipo = models.CharField(max_length=30, choices=TIPOS, default="general")
    periodo = models.CharField(max_length=30, choices=PERIODOS, default="mensual")
    activo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Reporte KPI")
        verbose_name_plural = _("Reportes KPI")

    def __str__(self):
        # __str__: Representación en string del objeto. Returns: str.
        return self.nombre


class KpiSnapshot(AgenciaMixin):
    """Valor histórico de una métrica en un momento dado."""

    METRICAS = [
        ("ventas_totales", _("Ventas Totales")),
        ("ventas_mensuales", _("Ventas Mensuales")),
        ("ventas_diarias", _("Ventas Diarias")),
        ("promedio_venta", _("Ticket Promedio")),
        ("margen_bruto", _("Margen Bruto %")),
        ("utilidad_total", _("Utilidad Total")),
        ("boletos_importados", _("Boletos Importados")),
        ("tasa_exito_importacion", _("Tasa de Éxito Importación")),
        ("clientes_nuevos", _("Clientes Nuevos")),
        ("clientes_totales", _("Clientes Totales")),
        ("comisiones_pendientes", _("Comisiones Pendientes")),
        ("comisiones_liquidadas", _("Comisiones Liquidadas")),
    ]

    metrica = models.CharField(max_length=40, choices=METRICAS)
    valor = models.DecimalField(max_digits=14, decimal_places=2)
    fecha = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Snapshot KPI")
        verbose_name_plural = _("Snapshots KPI")
        unique_together = [("agencia", "metrica", "fecha")]
        ordering = ["-fecha"]

    def __str__(self):
        # __str__: Representación en string del objeto. Returns: str.
        return f"{self.get_metrica_display()}: {self.valor} ({self.fecha})"


class ReporteProgramado:
    """Clase ReporteProgramado. Uso: según contexto de la aplicación.
    """
    DIAS_SEMANA = [
        (1, _("Lunes")),
        (2, _("Martes")),
        (3, _("Miércoles")),
        (4, _("Jueves")),
        (5, _("Viernes")),
        (6, _("Sábado")),
        (7, _("Domingo")),
    ]

    nombre = models.CharField(max_length=120)
    tipo = models.CharField(max_length=30, choices=ReporteKPI.TIPOS, default="general")
    frecuencia = models.CharField(max_length=20, choices=ReporteKPI.PERIODOS, default="semanal")
    dia_semana = models.IntegerField(choices=DIAS_SEMANA, null=True, blank=True, help_text="Para frecuencia semanal")
    activo = models.BooleanField(default=True)
    destinatarios = models.JSONField(default=list, help_text="Lista de emails")
    ultimo_envio = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Reporte Programado")
        verbose_name_plural = _("Reportes Programados")

    def __str__(self):
        # __str__: Representación en string del objeto. Returns: str.
        return f"{self.nombre} ({self.get_frecuencia_display()})"

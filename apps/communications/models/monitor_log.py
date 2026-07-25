"""Módulo monitor log de la aplicación communications.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _

from core.api import AgenciaMixin


class EmailMonitorLog(AgenciaMixin, models.Model):
    """
    Modelo para registrar el historial de ejecuciones y diagnóstico del Mailbot.
    Permite auditar el estado de conexión de cada agencia y diagnosticar fallos.
    """

    class Estado(models.TextChoices):
        SUCCESS = "SUCCESS", _("Éxito")
        ERROR = "ERROR", _("Error")
        WARNING = "WARNING", _("Advertencia")

    fecha_ejecucion = models.DateTimeField(auto_now_add=True, db_index=True)
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.SUCCESS)
    mensaje = models.TextField()
    host_conectado = models.CharField(max_length=255, blank=True, null=True)
    correos_procesados = models.IntegerField(default=0)
    tiempo_ejecucion = models.FloatField(help_text="Tiempo de ejecución en segundos", default=0.0)

    class Meta:
        verbose_name = _("Log de Monitor de Correo")
        verbose_name_plural = _("Logs de Monitor de Correo")
        ordering = ["-fecha_ejecucion"]

    def __str__(self):
        # __str__: Representación en string del objeto. Returns: str.
        fecha_str = (
            self.fecha_ejecucion.strftime("%Y-%m-%d %H:%M:%S") if self.fecha_ejecucion else "N/A"
        )
        return f"{self.agencia.nombre if self.agencia else 'Global'} - {fecha_str} - {self.get_estado_display()}"

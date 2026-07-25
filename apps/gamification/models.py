"""Modelos de base de datos para la aplicación gamification.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _

from core.models.base import AgenciaMixin


class Nivel:
    """Clase Nivel. Uso: según contexto de la aplicación.
    """
    nombre = models.CharField(max_length=60)
    icono = models.CharField(max_length=100, default="stars")
    color = models.CharField(max_length=7, default="#6B7280", help_text="Hex color")
    puntos_minimos = models.PositiveIntegerField(unique=True)
    descripcion = models.TextField(blank=True)

    class Meta:
        verbose_name = _("Nivel")
        verbose_name_plural = _("Niveles")
        ordering = ["puntos_minimos"]

    def __str__(self):
        # __str__: Representación en string del objeto. Returns: str.
        return self.nombre


class Logro:
    """Clase Logro. Uso: según contexto de la aplicación.
    """
    CATEGORIAS = [
        ("ventas", _("Ventas")),
        ("importacion", _("Importación")),
        ("clientes", _("Clientes")),
        ("contenido", _("Contenido")),
        ("configuracion", _("Configuración")),
        ("equipo", _("Equipo")),
        ("especial", _("Especial")),
    ]

    codigo = models.SlugField(max_length=60, unique=True, help_text="Código único del logro (ej: primera_venta)")
    nombre = models.CharField(max_length=120)
    descripcion = models.TextField(blank=True)
    icono = models.CharField(max_length=60, default="emoji_events", help_text="Material Symbol name")
    categoria = models.CharField(max_length=30, choices=CATEGORIAS, default="especial")
    puntos = models.PositiveIntegerField(default=10)
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = _("Logro")
        verbose_name_plural = _("Logros")

    def __str__(self):
        # __str__: Representación en string del objeto. Returns: str.
        return self.nombre


class LogroProgreso:
    """Clase LogroProgreso. Uso: según contexto de la aplicación.
    """
    usuario = models.ForeignKey("auth.User", on_delete=models.CASCADE, related_name="logros")
    logro = models.ForeignKey(Logro, on_delete=models.CASCADE, related_name="progresos")
    progreso = models.PositiveIntegerField(default=0, help_text="Progreso actual (0-100)")
    completado = models.BooleanField(default=False)
    fecha_completado = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = _("Progreso de Logro")
        verbose_name_plural = _("Progresos de Logros")
        unique_together = [("usuario", "logro", "agencia")]
        ordering = ["-completado", "-progreso"]

    def __str__(self):
        # __str__: Representación en string del objeto. Returns: str.
        return f"{self.usuario} - {self.logro} ({self.progreso}%)"


class PuntuacionUsuario:
    """Clase PuntuacionUsuario. Uso: según contexto de la aplicación.
    """
    usuario = models.ForeignKey("auth.User", on_delete=models.CASCADE, related_name="puntuacion")
    puntos_total = models.PositiveIntegerField(default=0)
    nivel = models.ForeignKey(Nivel, on_delete=models.SET_NULL, null=True, blank=True)
    logros_completados = models.PositiveIntegerField(default=0)
    ultima_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Puntuación de Usuario")
        verbose_name_plural = _("Puntuaciones de Usuarios")
        unique_together = [("usuario", "agencia")]

    def __str__(self):
        # __str__: Representación en string del objeto. Returns: str.
        return f"{self.usuario}: {self.puntos_total} pts"

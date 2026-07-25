"""Modelos de base de datos para la aplicación automation.
"""

from django.contrib.auth.models import User
from django.db import models
from django.utils.translation import gettext_lazy as _

from core.api import AgenciaMixin


class NotificacionInteligente(AgenciaMixin, models.Model):
    """
    Modelo para notificaciones en tiempo real vía polling HTMX.
    Diseñado para mostrar 'Magic Toasts' de IA y otros eventos asíncronos.
    """

    class Tipo(models.TextChoices):
        AI_MAGIC = "ai_magic", _("AI Magic ✨")
        SUCCESS = "success", _("Éxito")
        WARNING = "warning", _("Advertencia")
        INFO = "info", _("Información")

    usuario = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="notificaciones_inteligentes_auto",
        null=True,
        blank=True,
    )
    tipo = models.CharField(max_length=20, choices=Tipo.choices, default=Tipo.INFO)
    titulo = models.CharField(max_length=150)
    mensaje = models.TextField()
    ahorro_tiempo = models.CharField(max_length=50, blank=True, help_text=_("Ej: 5 min"))
    leida = models.BooleanField(default=False)
    creado_en = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = _("Notificación Inteligente")
        verbose_name_plural = _("Notificaciones Inteligentes")
        ordering = ["-creado_en"]
        indexes = [
            models.Index(fields=["usuario", "leida"]),
        ]

    def __str__(self):
        # __str__: Representación en string del objeto. Returns: str.
        return f"{self.titulo} - {self.usuario.username}"


class NotificacionAgente(AgenciaMixin, models.Model):
    """
    Modelo ligero para notificaciones flotantes (Magic Toasts).
    Utilizado para feedback inmediato de tareas asíncronas vía HTMX Polling.
    """

    class Tipo(models.TextChoices):
        AI_MAGIC = "ai_magic", _("AI Magic ✨")
        SUCCESS = "success", _("Éxito")
        WARNING = "warning", _("Advertencia")

    usuario = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="notificaciones_agente_auto",
        null=True,
        blank=True,
    )
    titulo = models.CharField(max_length=150)
    mensaje = models.TextField()
    icono = models.CharField(max_length=50, default="auto_awesome")
    tipo = models.CharField(max_length=20, choices=Tipo.choices, default=Tipo.AI_MAGIC)
    leida = models.BooleanField(default=False)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Notificación de Agente")
        verbose_name_plural = _("Notificaciones de Agente")
        ordering = ["-creado_en"]

    def __str__(self):
        # __str__: Representación en string del objeto. Returns: str.
        return f"{self.titulo} -> {self.usuario.username}"

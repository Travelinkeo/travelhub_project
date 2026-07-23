from django.db import models
from django.utils.translation import gettext_lazy as _

from core.models.base import AgenciaMixin


class Tarea(AgenciaMixin):
    PRIORIDADES = [
        ("baja", _("Baja")),
        ("media", _("Media")),
        ("alta", _("Alta")),
        ("urgente", _("Urgente")),
    ]

    ESTADOS = [
        ("pendiente", _("Pendiente")),
        ("en_progreso", _("En Progreso")),
        ("revision", _("En Revisión")),
        ("completada", _("Completada")),
        ("cancelada", _("Cancelada")),
    ]

    titulo = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    prioridad = models.CharField(max_length=20, choices=PRIORIDADES, default="media")
    estado = models.CharField(max_length=20, choices=ESTADOS, default="pendiente")
    asignado_a = models.ForeignKey(
        "auth.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="tareas_asignadas"
    )
    creado_por = models.ForeignKey("auth.User", on_delete=models.CASCADE, related_name="tareas_creadas")
    fecha_vencimiento = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Tarea")
        verbose_name_plural = _("Tareas")
        ordering = ["-prioridad", "created_at"]

    def __str__(self):
        return self.titulo


class ComentarioTarea(AgenciaMixin):
    tarea = models.ForeignKey(Tarea, on_delete=models.CASCADE, related_name="comentarios")
    usuario = models.ForeignKey("auth.User", on_delete=models.CASCADE)
    texto = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Comentario")
        verbose_name_plural = _("Comentarios")
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.usuario} - {self.created_at}"

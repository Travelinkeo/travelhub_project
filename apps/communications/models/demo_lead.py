"""Módulo demo lead de la aplicación communications.
"""

from django.db import models


class DemoRequest:
    """Clase DemoRequest. Uso: según contexto de la aplicación.
    """
    nombre = models.CharField(max_length=150)
    email = models.EmailField()
    telefono = models.CharField(max_length=30, blank=True, default="")
    agencia_nombre = models.CharField(max_length=200, blank=True, default="")
    volumen = models.CharField(max_length=30, blank=True, default="")
    mensaje = models.TextField(blank=True, default="")
    atendido = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Solicitud de Demo"
        verbose_name_plural = "Solicitudes de Demo"
        ordering = ["-created_at"]

    def __str__(self):
        # __str__: Representación en string del objeto. Returns: str.
        return f"{self.nombre} — {self.email}"

from django.db import models


class DemoRequest(models.Model):
    """DemoRequest."""

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
        """__str__."""
        return f"{self.nombre} — {self.email}"

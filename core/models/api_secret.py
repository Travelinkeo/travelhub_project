from django.db import models

from core.fields import EncryptedCharField


class APISecret(models.Model):
    CATEGORIES = [
        ("ai", "IA / ML"),
        ("payment", "Pagos"),
        ("email", "Correo"),
        ("storage", "Almacenamiento"),
        ("maps", "Mapas"),
        ("messaging", "Mensajería"),
        ("whatsapp", "WhatsApp"),
        ("gds", "GDS / Aerolíneas"),
        ("social", "Redes Sociales"),
        ("infra", "Infraestructura"),
        ("monitoring", "Monitoreo"),
        ("security", "Seguridad"),
    ]

    service = models.CharField(max_length=100, unique=True)
    category = models.CharField(max_length=20, choices=CATEGORIES)
    value = EncryptedCharField(max_length=3000)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    last_tested = models.DateTimeField(null=True, blank=True)
    test_status = models.CharField(max_length=20, default="unknown")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Clave API"
        verbose_name_plural = "Claves API"
        ordering = ["category", "service"]

    def __str__(self):
        prefix = self.value[:8] if self.value else ""
        return f"[{self.get_category_display()}] {self.service} ({prefix}...)"

from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _

class PasaporteEscaneado(models.Model):
    class ConfianzaChoices(models.TextChoices):
        HIGH = "HIGH", _("Alta")
        MEDIUM = "MEDIUM", _("Media")
        LOW = "LOW", _("Baja")

    class SexoChoices(models.TextChoices):
        M = "M", _("Masculino")
        F = "F", _("Femenino")

    imagen_original = models.ImageField(upload_to="pasaportes/%Y/%m/")
    imagen_procesada = models.ImageField(
        upload_to="pasaportes/processed/%Y/%m/",
        blank=True,
        null=True
    )
    numero_pasaporte = models.CharField(max_length=20, blank=True)
    nombres = models.CharField(max_length=100, blank=True)
    apellidos = models.CharField(max_length=100, blank=True)
    nacionalidad = models.CharField(max_length=3, blank=True)
    fecha_nacimiento = models.DateField(blank=True, null=True)
    fecha_vencimiento = models.DateField(blank=True, null=True)
    sexo = models.CharField(
        max_length=1,
        choices=SexoChoices.choices,
        blank=True
    )
    lugar_nacimiento = models.CharField(max_length=100, blank=True)
    confianza_ocr = models.CharField(
        max_length=10,
        choices=ConfianzaChoices.choices,
        default=ConfianzaChoices.MEDIUM
    )
    datos_ocr_completos = models.JSONField(default=dict)
    texto_mrz = models.TextField(blank=True)
    errores_detectados = models.JSONField(default=list)
    fecha_procesamiento = models.DateTimeField(auto_now_add=True)
    verificado_manualmente = models.BooleanField(default=False)
    
    cliente = models.ForeignKey(
        'crm.Cliente',
        on_delete=models.CASCADE,
        blank=True,
        null=True
    )
    procesado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True
    )

    class Meta:
        verbose_name = _("Pasaporte Escaneado")
        verbose_name_plural = _("Pasaportes Escaneados")
        db_table = "core_pasaporte_escaneado"
        ordering = ["-fecha_procesamiento"]

    def __str__(self):
        return f"Pasaporte {self.numero_pasaporte} - {self.nombres} {self.apellidos}"

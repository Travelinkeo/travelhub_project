"""Modelos de base de datos para la aplicación marketing.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _

from core.api import AgenciaMixin


class Campania:
    """Clase Campania. Uso: según contexto de la aplicación.
    """
    class EstadoCampania(models.TextChoices):
        BORRADOR = "BORRADOR", _("Borrador")
        PROGRAMADA = "PROGRAMADA", _("Programada")
        ACTIVA = "ACTIVA", _("Activa")
        FINALIZADA = "FINALIZADA", _("Finalizada")

    nombre = models.CharField(_("Nombre de la Campaña"), max_length=255)
    descripcion = models.TextField(_("Descripción"), blank=True)
    fecha_inicio = models.DateTimeField(_("Fecha de Inicio"), null=True, blank=True)
    fecha_fin = models.DateTimeField(_("Fecha de Fin"), null=True, blank=True)
    estado = models.CharField(
        _("Estado"), max_length=20, choices=EstadoCampania.choices, default=EstadoCampania.BORRADOR
    )

    # Redes sociales destino
    publicar_en_instagram = models.BooleanField(default=True)
    publicar_en_facebook = models.BooleanField(default=False)
    publicar_en_whatsapp = models.BooleanField(default=True)

    def __str__(self):
        # __str__: Representación en string del objeto. Returns: str.
        return self.nombre

    class Meta:
        verbose_name = _("Campaña")
        verbose_name_plural = _("Campañas")


class ActivoMarketing:
    """Clase ActivoMarketing. Uso: según contexto de la aplicación.
    """
    class TipoActivo(models.TextChoices):
        FLYER = "FLYER", _("Flyer (Imagen)")
        STORY = "STORY", _("Story (Instagram)")
        COPY = "COPY", _("Texto (Copywriting)")
        VIDEO = "VIDEO", _("Video/Reel")

    campania = models.ForeignKey(
        Campania, on_delete=models.SET_NULL, null=True, blank=True, related_name="activos"
    )
    hotel = models.ForeignKey(
        "bookings.HotelTarifario",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="activos_marketing",
    )
    tipo = models.CharField(_("Tipo de Activo"), max_length=20, choices=TipoActivo.choices)

    # Contenido
    archivo = models.FileField(_("Archivo"), upload_to="marketing/assets/", null=True, blank=True)
    texto_caption = models.TextField(_("Caption / Texto"), blank=True)

    # Metadata IA
    prompt_utilizado = models.TextField(_("Prompt Utilizado"), blank=True)
    datos_ia = models.JSONField(
        _("Datos Estructura IA"),
        blank=True,
        null=True,
        help_text=_("Estructura completa devuelta por la IA (variantes, hashtags, etc.)"),
    )
    generado_por_ia = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    # Integración Telegram
    telegram_file_id = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        # __str__: Representación en string del objeto. Returns: str.
        return f"{self.tipo} - {self.hotel.nombre if self.hotel else 'Genérico'}"

    class Meta:
        verbose_name = _("Activo de Marketing")
        verbose_name_plural = _("Activos de Marketing")


class ConfiguracionMarketing:
    """Clase ConfiguracionMarketing. Uso: según contexto de la aplicación.
    """
    color_primario = models.CharField(max_length=7, default="#0f172a")  # Hexadecimal
    color_secundario = models.CharField(max_length=7, default="#fbbf24")
    fuente_principal = models.CharField(max_length=100, default="Arial")

    hashtag_default = models.TextField(
        _("Hashtags por defecto"), blank=True, help_text=_("Separa con espacios")
    )

    def __str__(self):
        # __str__: Representación en string del objeto. Returns: str.
        return f"Config Marketing - {self.agencia.nombre}"

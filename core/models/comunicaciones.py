
from django.db import models
from django.utils.translation import gettext_lazy as _


class ComunicacionProveedor(models.Model):
    class Categoria(models.TextChoices):
        URGENTE = 'URG', _('Notificación Urgente')
        INFO = 'INF', _('Información General')
        PROMO = 'PRO', _('Promoción')
        OTRO = 'OTR', _('Otro')

    id = models.AutoField(primary_key=True)
    remitente = models.CharField(max_length=255)
    asunto = models.CharField(max_length=500)
    fecha_recepcion = models.DateTimeField(auto_now_add=True)
    
    categoria = models.CharField(
        max_length=3,
        choices=Categoria.choices,
        default=Categoria.OTRO
    )
    
    contenido_extraido = models.JSONField(
        _("Contenido Extraído por IA"),
        help_text=_("El JSON estructurado devuelto por el análisis de Gemini."),
        null=True, blank=True
    )
    
    cuerpo_completo = models.TextField(
        _("Cuerpo completo del correo"),
        blank=True
    )

    # --- Campos para Contenido Generado por IA (Promociones) ---
    whatsapp_status = models.TextField(
        _("Contenido para Estado de WhatsApp"),
        blank=True, null=True,
        help_text=_("Texto corto y llamativo para WhatsApp generado por IA.")
    )
    instagram_post = models.TextField(
        _("Contenido para Post de Instagram"),
        blank=True, null=True,
        help_text=_("Descripción para Instagram con hashtags generada por IA.")
    )
    instagram_reel_idea = models.JSONField(
        _("Idea para Reel de Instagram"),
        blank=True, null=True,
        help_text=_("Guion o concepto para un Reel de 15s generado por IA.")
    )

    class Meta:
        verbose_name = "Comunicación de Proveedor"
        verbose_name_plural = "Comunicaciones de Proveedores"
        ordering = ['-fecha_recepcion']

    def __str__(self):
        return f"[{self.get_categoria_display()}] {self.asunto} - {self.remitente}"

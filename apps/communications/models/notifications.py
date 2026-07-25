"""
Notification Preferences & Templates
Modelos para gestión de preferencias de notificación multi-canal y plantillas personalizables.
"""

from django.conf import settings
from django.db import models

from core.models import Agencia
from core.models.base import GlobalAwareAgenciaManager


class NotificationPreference(models.Model):
    """
    Preferencias de notificación por usuario y tipo de evento.
    Permite a cada usuario elegir qué canales recibir para cada evento.
    """

    CHANNEL_CHOICES = [
        ("email", "Email"),
        ("whatsapp", "WhatsApp"),
        ("sms", "SMS"),
        ("push", "Push Notification"),
        ("in_app", "In-App"),
        ("slack", "Slack"),
        ("teams", "Teams"),
    ]

    EVENT_CHOICES = [
        ("venta_creada", "Venta Creada"),
        ("venta_actualizada", "Venta Actualizada"),
        ("venta_anulada", "Venta Anulada"),
        ("pago_confirmado", "Pago Confirmado"),
        ("pago_pendiente", "Pago Pendiente"),
        ("recordatorio_pago", "Recordatorio de Pago"),
        ("boleto_importado", "Boleto Importado"),
        ("boleto_revisado", "Boleto Revisado"),
        ("cotizacion_enviada", "Cotización Enviada"),
        ("cotizacion_aprobada", "Cotización Aprobada"),
        ("factura_generada", "Factura Generada"),
        ("cliente_creado", "Cliente Creado"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notification_preferences",
        help_text="Usuario propietario de estas preferencias",
    )
    agencia = models.ForeignKey(
        Agencia,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notification_preferences",
        help_text="Agencia a la que aplican estas preferencias (null = globales)",
    )
    event_type = models.CharField(
        max_length=50,
        choices=EVENT_CHOICES,
        help_text="Tipo de evento que dispara la notificación",
    )
    channel = models.CharField(
        max_length=20,
        choices=CHANNEL_CHOICES,
        help_text="Canal de notificación preferido",
    )
    enabled = models.BooleanField(
        default=True,
        help_text="Si está desactivado, no se enviarán notificaciones para este combo",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Preferencia de Notificación"
        verbose_name_plural = "Preferencias de Notificación"
        unique_together = ["user", "agencia", "event_type", "channel"]
        indexes = [
            models.Index(fields=["user", "event_type"]),
            models.Index(fields=["agencia", "event_type"]),
        ]

    def __str__(self):
        # __str__: Representación en string del objeto. Returns: str.
        agencia_str = f" - {self.agencia.nombre}" if self.agencia else ""
        return f"{self.user.username} - {self.event_type} - {self.channel}{agencia_str}"


class NotificationTemplate(models.Model):
    """
    Plantillas personalizables para notificaciones.
    Soporta variables dinámicas en formato {{variable}}.
    """

    LANGUAGE_CHOICES = [
        ("es", "Español"),
        ("en", "English"),
        ("pt", "Português"),
    ]

    CHANNEL_CHOICES = [
        ("email", "Email"),
        ("whatsapp", "WhatsApp"),
        ("sms", "SMS"),
    ]

    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="Nombre interno de la plantilla (ej: 'venta_confirmacion')",
    )
    event_type = models.CharField(
        max_length=50,
        help_text="Tipo de evento asociado (ej: 'venta_creada')",
    )
    channel = models.CharField(
        max_length=20,
        choices=CHANNEL_CHOICES,
        help_text="Canal para el que está diseñada esta plantilla",
    )
    language = models.CharField(
        max_length=2,
        choices=LANGUAGE_CHOICES,
        default="es",
        help_text="Idioma de la plantilla",
    )
    subject_template = models.CharField(
        max_length=200,
        blank=True,
        help_text="Asunto (solo Email). Variables: {{variable}}",
    )
    body_template = models.TextField(
        help_text="Cuerpo del mensaje. Variables: {{variable}}",
    )
    html_template = models.TextField(
        blank=True,
        help_text="HTML para emails (opcional). Variables: {{variable}}",
    )
    whatsapp_template_id = models.CharField(
        max_length=100,
        blank=True,
        help_text="ID de plantilla en WhatsApp Business API (opcional)",
    )
    variables_disponibles = models.TextField(
        blank=True,
        help_text="Lista de variables disponibles (documentación interna)",
    )
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(
        default=False,
        help_text="Si es True, se usa como fallback si no hay personalizada",
    )
    agencia = models.ForeignKey(
        Agencia,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notification_templates",
        help_text="Si null, es plantilla global. Si tiene agencia, es personalizada.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Aislamiento multi-tenant: filtra por agencia del contexto (incluye
    # plantillas globales con agencia=None).
    objects = GlobalAwareAgenciaManager()
    all_objects = models.Manager()

    class Meta:
        verbose_name = "Plantilla de Notificación"
        verbose_name_plural = "Plantillas de Notificación"
        indexes = [
            models.Index(fields=["event_type", "channel", "language"]),
            models.Index(fields=["name"]),
        ]

    def __str__(self):
        # __str__: Representación en string del objeto. Returns: str.
        return f"{self.name} ({self.channel} - {self.language})"

    def render(self, context: dict) -> dict:
        """
        Renderiza la plantilla con el contexto dado.
        Reemplaza {{variable}} con el valor del contexto.
        """
        import re

        def replace_var(match):
            # replace_var: Replace var. Args: según implementación. Returns: según implementación.
            var_name = match.group(1)
            return str(context.get(var_name, match.group(0)))

        result = {
            "subject": re.sub(r"\{\{(\w+)\}\}", replace_var, self.subject_template)
            if self.subject_template
            else "",
            "body": re.sub(r"\{\{(\w+)\}\}", replace_var, self.body_template),
            "html": re.sub(r"\{\{(\w+)\}\}", replace_var, self.html_template)
            if self.html_template
            else "",
        }
        return result


class NotificationLog(models.Model):
    """
    Log de todas las notificaciones enviadas.
    Útil para auditoría, debugging y métricas.
    """

    STATUS_CHOICES = [
        ("pending", "Pendiente"),
        ("sent", "Enviada"),
        ("failed", "Fallida"),
        ("retrying", "Reintentando"),
        ("cancelled", "Cancelada"),
    ]

    event_type = models.CharField(max_length=50, help_text="Evento que disparó la notificación")
    channel = models.CharField(max_length=20, help_text="Canal utilizado")
    recipient = models.CharField(max_length=255, help_text="Destinatario (email, teléfono, etc.)")
    subject = models.CharField(max_length=500, blank=True, help_text="Asunto (si aplica)")
    body = models.TextField(help_text="Cuerpo del mensaje enviado")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    error_message = models.TextField(blank=True, help_text="Mensaje de error si falló")
    retry_count = models.IntegerField(default=0, help_text="Cantidad de reintentos")
    sent_at = models.DateTimeField(null=True, blank=True, help_text="Fecha de envío exitoso")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Relaciones opcionales para trazabilidad
    agencia = models.ForeignKey(
        Agencia,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notification_logs",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notification_logs",
    )
    # Referencia genérica al objeto que originó la notificación
    content_type = models.CharField(
        max_length=100, blank=True, help_text="Tipo de objeto (ej: 'venta')"
    )
    object_id = models.CharField(max_length=100, blank=True, help_text="ID del objeto relacionado")

    # Aislamiento multi-tenant: filtra por agencia del contexto (incluye
    # logs globales con agencia=None).
    objects = GlobalAwareAgenciaManager()
    all_objects = models.Manager()

    class Meta:
        verbose_name = "Log de Notificación"
        verbose_name_plural = "Logs de Notificaciones"
        indexes = [
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["event_type", "created_at"]),
            models.Index(fields=["channel", "created_at"]),
        ]

    def __str__(self):
        # __str__: Representación en string del objeto. Returns: str.
        return f"{self.event_type} -> {self.recipient} ({self.status})"

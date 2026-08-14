import uuid

from django.db import models
from django.utils import timezone


class VentaMensaje(models.Model):
    """
    Representa un mensaje en el hilo conversacional del expediente de venta,
    transportado vía Correo Electrónico (RFC 2822) o WhatsApp.
    """

    DIRECCION_CHOICES = [
        ("IN", "Cliente / Pasajero"),
        ("OUT", "Agente / Sistema"),
    ]

    CANAL_CHOICES = [
        ("EMAIL", "Correo Electrónico"),
        ("WHATSAPP", "WhatsApp"),
    ]

    venta = models.ForeignKey(
        "bookings.Venta",
        on_delete=models.CASCADE,
        related_name="mensajes_comunicacion",
        verbose_name="Expediente de Venta",
    )
    direccion = models.CharField(
        max_length=3, choices=DIRECCION_CHOICES, default="OUT", verbose_name="Dirección"
    )
    canal = models.CharField(
        max_length=10, choices=CANAL_CHOICES, default="EMAIL", verbose_name="Canal"
    )
    remitente = models.CharField(max_length=255, verbose_name="Remitente")
    destinatario = models.CharField(max_length=255, verbose_name="Destinatario")
    cuerpo = models.TextField(verbose_name="Contenido del Mensaje")

    # Cabeceras técnicas para mantener el hilo en Gmail/Outlook/Apple Mail
    message_id = models.CharField(
        max_length=255, unique=True, default=uuid.uuid4, verbose_name="Message-ID RFC"
    )
    in_reply_to = models.CharField(
        max_length=255, blank=True, null=True, verbose_name="In-Reply-To"
    )

    # Enlace a la Ficha Digital si fue incluida
    enlace_ficha_digital = models.URLField(
        blank=True, null=True, verbose_name="Enlace a Ficha Digital"
    )

    created_at = models.DateTimeField(
        default=timezone.now, db_index=True, verbose_name="Fecha y Hora"
    )

    class Meta:
        verbose_name = "Mensaje de Venta"
        verbose_name_plural = "Mensajes de Venta"
        ordering = ["created_at"]

    def __str__(self):
        return f"[{self.get_direccion_display()}] {self.venta.localizador} - {self.remitente} ({self.created_at.strftime('%d/%m %H:%M')})"


class MensajeAdjunto(models.Model):
    """
    Documento o archivo adjunto asociado a un mensaje del expediente
    (Boletos PDF, Facturas, Vouchers, Pasaportes).
    """

    TIPO_CHOICES = [
        ("BOLETO", "Boleto PDF"),
        ("FACTURA", "Factura / Recibo"),
        ("VOUCHER", "Voucher de Servicios"),
        ("PASAPORTE", "Documento de Identidad"),
        ("OTRO", "Otro Adjunto"),
    ]

    mensaje = models.ForeignKey(
        VentaMensaje, on_delete=models.CASCADE, related_name="adjuntos", verbose_name="Mensaje"
    )
    archivo = models.FileField(upload_to="booking_docs/%Y/%m/", verbose_name="Archivo")
    nombre_archivo = models.CharField(max_length=255, verbose_name="Nombre del Archivo")
    tipo_documento = models.CharField(
        max_length=15, choices=TIPO_CHOICES, default="BOLETO", verbose_name="Tipo de Documento"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Carga")

    class Meta:
        verbose_name = "Adjunto de Mensaje"
        verbose_name_plural = "Adjuntos de Mensaje"
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.nombre_archivo} ({self.get_tipo_documento_display()})"

import uuid
import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("bookings", "0050_boletoimportado_es_reemision"),
    ]

    operations = [
        migrations.CreateModel(
            name="VentaMensaje",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "direccion",
                    models.CharField(
                        choices=[("IN", "Cliente / Pasajero"), ("OUT", "Agente / Sistema")],
                        default="OUT",
                        max_length=3,
                        verbose_name="Dirección",
                    ),
                ),
                (
                    "canal",
                    models.CharField(
                        choices=[("EMAIL", "Correo Electrónico"), ("WHATSAPP", "WhatsApp")],
                        default="EMAIL",
                        max_length=10,
                        verbose_name="Canal",
                    ),
                ),
                ("remitente", models.CharField(max_length=255, verbose_name="Remitente")),
                ("destinatario", models.CharField(max_length=255, verbose_name="Destinatario")),
                ("cuerpo", models.TextField(verbose_name="Contenido del Mensaje")),
                (
                    "message_id",
                    models.CharField(
                        default=uuid.uuid4,
                        max_length=255,
                        unique=True,
                        verbose_name="Message-ID RFC",
                    ),
                ),
                (
                    "in_reply_to",
                    models.CharField(
                        blank=True,
                        max_length=255,
                        null=True,
                        verbose_name="In-Reply-To",
                    ),
                ),
                (
                    "enlace_ficha_digital",
                    models.URLField(
                        blank=True,
                        null=True,
                        verbose_name="Enlace a Ficha Digital",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        db_index=True,
                        default=django.utils.timezone.now,
                        verbose_name="Fecha y Hora",
                    ),
                ),
                (
                    "venta",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="mensajes_comunicacion",
                        to="bookings.venta",
                        verbose_name="Expediente de Venta",
                    ),
                ),
            ],
            options={
                "verbose_name": "Mensaje de Venta",
                "verbose_name_plural": "Mensajes de Venta",
                "ordering": ["created_at"],
            },
        ),
        migrations.CreateModel(
            name="MensajeAdjunto",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "archivo",
                    models.FileField(
                        upload_to="booking_docs/%Y/%m/",
                        verbose_name="Archivo",
                    ),
                ),
                (
                    "nombre_archivo",
                    models.CharField(max_length=255, verbose_name="Nombre del Archivo"),
                ),
                (
                    "tipo_documento",
                    models.CharField(
                        choices=[
                            ("BOLETO", "Boleto PDF"),
                            ("FACTURA", "Factura / Recibo"),
                            ("VOUCHER", "Voucher de Servicios"),
                            ("PASAPORTE", "Documento de Identidad"),
                            ("OTRO", "Otro Adjunto"),
                        ],
                        default="BOLETO",
                        max_length=15,
                        verbose_name="Tipo de Documento",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Carga"),
                ),
                (
                    "mensaje",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="adjuntos",
                        to="bookings.ventamensaje",
                        verbose_name="Mensaje",
                    ),
                ),
            ],
            options={
                "verbose_name": "Adjunto de Mensaje",
                "verbose_name_plural": "Adjuntos de Mensaje",
                "ordering": ["created_at"],
            },
        ),
    ]

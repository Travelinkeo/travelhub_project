"""Migración de base de datos para crm.
"""

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration:
    """Clase Migration. Uso: según contexto de la aplicación.
    """
    dependencies = [
        ("crm", "0030_clean_null_charfields"),
    ]

    operations = [
        # Add fields to MensajeWhatsApp
        migrations.AddField(
            model_name="mensajewhatsapp",
            name="error_msg",
            field=models.TextField(blank=True, help_text="Mensaje de error si falló"),
        ),
        migrations.AddField(
            model_name="mensajewhatsapp",
            name="estado",
            field=models.CharField(
                choices=[
                    ("pending", "Pendiente"),
                    ("sent", "Enviado"),
                    ("delivered", "Entregado"),
                    ("read", "Leído"),
                    ("failed", "Fallido"),
                ],
                default="pending",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="mensajewhatsapp",
            name="message_id",
            field=models.CharField(
                blank=True, help_text="ID del mensaje en WhatsApp", max_length=255
            ),
        ),
        migrations.AddField(
            model_name="mensajewhatsapp",
            name="tipo_mensaje",
            field=models.CharField(
                blank=True,
                choices=[
                    ("text", "Texto"),
                    ("buttons", "Botones"),
                    ("list", "Lista"),
                    ("image", "Imagen"),
                    ("document", "Documento"),
                    ("location", "Ubicación"),
                    ("contact", "Contacto"),
                    ("sticker", "Sticker"),
                    ("reaction", "Reacción"),
                ],
                default="text",
                max_length=30,
            ),
        ),
        # Add indexes
        migrations.AddIndex(
            model_name="mensajewhatsapp",
            index=models.Index(fields=["estado", "agencia_id"], name="idx_wa_estado"),
        ),
        migrations.AddIndex(
            model_name="mensajewhatsapp",
            index=models.Index(fields=["message_id"], name="idx_wa_message_id"),
        ),
        # Create WhatsAppScheduledMessage model
        migrations.CreateModel(
            name="WhatsAppScheduledMessage",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(default=False)),
                (
                    "telefono",
                    models.CharField(
                        help_text="Número de teléfono del destinatario", max_length=20
                    ),
                ),
                ("texto", models.TextField(help_text="Contenido del mensaje")),
                (
                    "programado_para",
                    models.DateTimeField(help_text="Fecha y hora programada para el envío"),
                ),
                (
                    "estado",
                    models.CharField(
                        choices=[
                            ("scheduled", "Programado"),
                            ("sending", "Enviando"),
                            ("sent", "Enviado"),
                            ("failed", "Fallido"),
                            ("cancelled", "Cancelado"),
                        ],
                        default="scheduled",
                        max_length=20,
                    ),
                ),
                ("error_msg", models.TextField(blank=True, help_text="Mensaje de error si falló")),
            ],
            options={
                "verbose_name": "Mensaje WhatsApp Programado",
                "verbose_name_plural": "Mensajes WhatsApp Programados",
            },
        ),
        # Add agencia FK to WhatsAppScheduledMessage
        migrations.AddField(
            model_name="whatsappscheduledmessage",
            name="agencia",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="%(class)s_set",
                to="core.agencia",
            ),
        ),
        # Add cliente FK to WhatsAppScheduledMessage
        migrations.AddField(
            model_name="whatsappscheduledmessage",
            name="cliente",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="whatsapp_programados",
                to="crm.cliente",
            ),
        ),
        # Add mensaje_resultante FK to WhatsAppScheduledMessage
        migrations.AddField(
            model_name="whatsappscheduledmessage",
            name="mensaje_resultante",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="programado_por",
                to="crm.mensajewhatsapp",
                help_text="Mensaje ya enviado resultante",
            ),
        ),
        # Add created_by FK to WhatsAppScheduledMessage
        migrations.AddField(
            model_name="whatsappscheduledmessage",
            name="created_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        # Add indexes for WhatsAppScheduledMessage
        migrations.AddIndex(
            model_name="whatsappscheduledmessage",
            index=models.Index(fields=["estado", "programado_para"], name="idx_wa_scheduled"),
        ),
        migrations.AddIndex(
            model_name="whatsappscheduledmessage",
            index=models.Index(fields=["agencia", "estado"], name="idx_wa_scheduled_agencia"),
        ),
    ]

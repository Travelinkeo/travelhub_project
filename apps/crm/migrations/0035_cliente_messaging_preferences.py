# Generated manually - adds telegram_subscribed_at, whatsapp_opt_in, preferred_channel to Cliente
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("crm", "0034_remove_whatsappscheduledmessage_is_deleted_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="cliente",
            name="telegram_subscribed_at",
            field=models.DateTimeField(
                blank=True,
                help_text="Fecha y hora de autoconexion del cliente al bot de Telegram",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="cliente",
            name="whatsapp_opt_in",
            field=models.BooleanField(
                default=True,
                help_text="Indica si el cliente acepta notificaciones por WhatsApp",
            ),
        ),
        migrations.AddField(
            model_name="cliente",
            name="preferred_channel",
            field=models.CharField(
                choices=[("email", "Email"), ("whatsapp", "WhatsApp"), ("telegram", "Telegram")],
                default="whatsapp",
                help_text="Canal preferido del cliente para recibir notificaciones",
                max_length=20,
            ),
        ),
    ]

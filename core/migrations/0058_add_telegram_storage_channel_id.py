# Generated manually - adds telegram_storage_channel_id to AgenciaConfiguracion
# for dedicated Telegram file storage channel per agency (multitenant isolation)
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0057_apisecret"),
    ]

    operations = [
        migrations.AddField(
            model_name="agenciaconfiguracion",
            name="telegram_storage_channel_id",
            field=models.CharField(
                blank=True,
                help_text="ID del canal privado de Telegram para almacenamiento de archivos.",
                max_length=255,
                null=True,
            ),
        ),
    ]

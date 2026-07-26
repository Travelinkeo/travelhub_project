from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0041_remove_legacy_tables"),
    ]

    operations = [
        migrations.AddField(
            model_name="agenciaconfiguracion",
            name="canal_notificaciones_mailbot",
            field=models.CharField(
                choices=[
                    ("telegram", "Telegram"),
                    ("whatsapp", "WhatsApp"),
                    ("both", "Ambos"),
                    ("none", "Ninguno"),
                ],
                default="telegram",
                help_text="Canal para notificar al operador cuando el mailbot detecta correos nuevos",
                max_length=10,
            ),
        ),
    ]

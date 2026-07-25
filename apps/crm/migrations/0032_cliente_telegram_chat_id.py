"""Migración de base de datos para crm.
"""

from django.db import migrations, models


class Migration:
    """Clase Migration. Uso: según contexto de la aplicación.
    """
    dependencies = [
        ("crm", "0031_whatsapp_enhancements"),
    ]

    operations = [
        migrations.AddField(
            model_name="cliente",
            name="telegram_chat_id",
            field=models.CharField(
                blank=True,
                help_text="Chat ID del cliente en Telegram para notificaciones",
                max_length=50,
            ),
        ),
    ]

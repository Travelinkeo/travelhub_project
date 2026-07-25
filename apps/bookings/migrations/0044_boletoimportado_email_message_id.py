"""Migración de base de datos para bookings.
"""

from django.db import migrations, models


class Migration:
    """Clase Migration. Uso: según contexto de la aplicación.
    """
    dependencies = [
        ("bookings", "0043_alter_boletoimportado_raw_hash_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="boletoimportado",
            name="email_message_id",
            field=models.CharField(
                blank=True,
                db_index=True,
                help_text="RFC 2822 Message-ID para deduplicación entre IMAP poll y webhook.",
                max_length=500,
                null=True,
                verbose_name="Message-ID del Email",
            ),
        ),
        migrations.AddConstraint(
            model_name="boletoimportado",
            constraint=models.UniqueConstraint(
                condition=models.Q(email_message_id__isnull=False),
                fields=("agencia", "email_message_id"),
                name="uq_boleto_agencia_message_id",
            ),
        ),
    ]

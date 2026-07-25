from django.db import migrations, models


class Migration:
    """Migración de base de datos generada por Django."""
    dependencies = [
        ("core", "0051_api_keys_pbkdf2"),
    ]

    operations = [
        migrations.AddField(
            model_name="cronapikey",
            name="lookup_hash",
            field=models.CharField(
                blank=True,
                editable=False,
                help_text="SHA-256 del raw key para O(1) lookup en verify()",
                max_length=64,
                null=True,
                unique=True,
            ),
        ),
    ]

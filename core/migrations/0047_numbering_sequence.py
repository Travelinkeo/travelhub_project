from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Crea NumberingSequence para reemplazar advisory locks (pg_advisory_xact_lock)
    con select_for_update() — ORM puro.

    Esta tabla permite numeración secuencial atómica por prefijo
    (facturas, asientos contables, etc.) sin SQL nativo.
    """

    dependencies = [
        ("core", "0045_api_keys_webhooks_v2"),
    ]

    operations = [
        migrations.CreateModel(
            name="NumberingSequence",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "prefix",
                    models.CharField(
                        help_text="Prefijo único (ej: F-20260608, AS-20260608)",
                        max_length=64,
                        unique=True,
                    ),
                ),
                (
                    "last_number",
                    models.IntegerField(
                        default=0,
                        help_text="Último número secuencial asignado",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True),
                ),
            ],
            options={
                "verbose_name": "Secuencia numérica",
                "verbose_name_plural": "Secuencias numéricas",
                "db_table": "core_numbering_sequence",
            },
        ),
    ]

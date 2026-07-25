"""Migración de base de datos para finance.
"""

import django.db.models.deletion
from django.db import migrations, models


class Migration:
    """Clase Migration. Uso: según contexto de la aplicación.
    """
    dependencies = [
        ("finance", "0024_alter_documentoexportacion_factura_and_more"),
        ("core", "0037_rename_remaining_core_tables"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AddField(
                    model_name="linkdepago",
                    name="agencia",
                    field=models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="linkdepago_items",
                        to="core.agencia",
                    ),
                ),
                migrations.AddField(
                    model_name="retencionislr",
                    name="agencia",
                    field=models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="retencionislr_items",
                        to="core.agencia",
                    ),
                ),
            ],
        ),
    ]

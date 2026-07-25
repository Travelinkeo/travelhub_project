"""Migración de base de datos para marketing.
"""

import django.db.models.deletion
from django.db import migrations, models


class Migration:
    """Clase Migration. Uso: según contexto de la aplicación.
    """
    dependencies = [
        ("marketing", "0005_alter_activomarketing_agencia_alter_campania_agencia_and_more"),
        ("core", "0037_rename_remaining_core_tables"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AddField(
                    model_name="activomarketing",
                    name="agencia",
                    field=models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="activomarketing_items",
                        to="core.agencia",
                    ),
                ),
            ],
        ),
    ]

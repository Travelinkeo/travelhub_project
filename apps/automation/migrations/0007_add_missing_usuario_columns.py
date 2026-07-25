"""Migración de base de datos para automation.
"""

import django.db.models.deletion
from django.db import migrations, models


class Migration:
    """Clase Migration. Uso: según contexto de la aplicación.
    """
    dependencies = [
        ("automation", "0006_alter_notificacionagente_table_and_more"),
        ("auth", "0012_alter_user_first_name_max_length"),
        ("core", "0037_rename_remaining_core_tables"),
    ]

    operations = [
        migrations.AddField(
            model_name="notificacioninteligente",
            name="usuario",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="notificaciones_inteligentes_auto",
                to="auth.user",
            ),
        ),
        migrations.AddField(
            model_name="notificacionagente",
            name="usuario",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="notificaciones_agente_auto",
                to="auth.user",
            ),
        ),
    ]

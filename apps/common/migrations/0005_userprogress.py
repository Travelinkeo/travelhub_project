"""Migración de base de datos para common.
"""

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration:
    """Clase Migration. Uso: según contexto de la aplicación.
    """
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("common", "0004_alter_aerolinea_table_alter_ciudad_table_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="UserProgress",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "current_step",
                    models.CharField(default="welcome", max_length=20),
                ),
                (
                    "completed_steps_json",
                    models.TextField(blank=True, default="[]"),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="onboarding_progress",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Progreso de Onboarding",
                "verbose_name_plural": "Progresos de Onboarding",
            },
        ),
    ]

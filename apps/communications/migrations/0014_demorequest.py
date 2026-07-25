"""Migración de base de datos para communications.
"""

from django.db import migrations, models


class Migration:
    """Clase Migration. Uso: según contexto de la aplicación.
    """
    dependencies = [
        ("communications", "0013_lead_followup_fields"),
    ]

    operations = [
        migrations.CreateModel(
            name="DemoRequest",
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
                ("nombre", models.CharField(max_length=150)),
                ("email", models.EmailField(max_length=254)),
                ("telefono", models.CharField(blank=True, default="", max_length=30)),
                ("agencia_nombre", models.CharField(blank=True, default="", max_length=200)),
                ("volumen", models.CharField(blank=True, default="", max_length=30)),
                ("mensaje", models.TextField(blank=True, default="")),
                ("atendido", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "verbose_name": "Solicitud de Demo",
                "verbose_name_plural": "Solicitudes de Demo",
                "ordering": ["-created_at"],
            },
        ),
    ]

# Generated manually — modelo APISecret para claves globales encriptadas.

import django.db.models.deletion
from django.db import migrations, models

import core.fields


class Migration:
    """Migración de base de datos generada por Django."""
    dependencies = [
        ("core", "0056_agenciasetupprogress"),
    ]

    operations = [
        migrations.CreateModel(
            name="APISecret",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("service", models.CharField(max_length=100, unique=True)),
                (
                    "category",
                    models.CharField(
                        choices=[
                            ("ai", "IA / ML"),
                            ("payment", "Pagos"),
                            ("email", "Correo"),
                            ("storage", "Almacenamiento"),
                            ("maps", "Mapas"),
                            ("messaging", "Mensajería"),
                            ("whatsapp", "WhatsApp"),
                            ("gds", "GDS / Aerolíneas"),
                            ("social", "Redes Sociales"),
                            ("infra", "Infraestructura"),
                            ("monitoring", "Monitoreo"),
                            ("security", "Seguridad"),
                        ],
                        max_length=20,
                    ),
                ),
                ("value", core.fields.EncryptedCharField(max_length=3000)),
                ("description", models.TextField(blank=True)),
                ("is_active", models.BooleanField(default=True)),
                ("last_tested", models.DateTimeField(null=True, blank=True)),
                (
                    "test_status",
                    models.CharField(default="unknown", max_length=20),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Clave API",
                "verbose_name_plural": "Claves API",
                "ordering": ["category", "service"],
            },
        ),
    ]

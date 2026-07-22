# Generated manually — modelo AgenciaSetupProgress para onboarding wizard.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0055_webhook_webhookdelivery_webhook_idx_webhook_agencia_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="AgenciaSetupProgress",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                (
                    "current_step",
                    models.CharField(
                        choices=[
                            ("welcome", "Bienvenida"),
                            ("profile", "Perfil de Agencia"),
                            ("team", "Tu Equipo"),
                            ("fiscal", "Configuración Fiscal"),
                            ("done", "¡Todo Listo!"),
                        ],
                        default="welcome",
                        max_length=20,
                    ),
                ),
                ("completed_steps", models.JSONField(default=list, blank=True)),
                ("skipped_steps", models.JSONField(default=list, blank=True)),
                ("started_at", models.DateTimeField(auto_now_add=True)),
                ("completed_at", models.DateTimeField(null=True, blank=True)),
                ("is_completed", models.BooleanField(default=False)),
                (
                    "agencia",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="%(class)s_items",
                        to="core.agencia",
                    ),
                ),
            ],
            options={
                "verbose_name": "Progreso de Onboarding",
                "verbose_name_plural": "Progresos de Onboarding",
            },
        ),
    ]

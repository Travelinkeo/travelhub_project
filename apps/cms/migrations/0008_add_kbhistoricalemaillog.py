import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("cms", "0006_add_kbdocument_and_knowledgechunk"),
        ("core", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="KBHistoricalEmailLog",
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
                    "message_id",
                    models.CharField(
                        db_index=True, max_length=255, verbose_name="Message-ID / UID"
                    ),
                ),
                (
                    "source_email",
                    models.CharField(
                        default="travelinkeo@gmail.com",
                        max_length=255,
                        verbose_name="Cuenta de Origen",
                    ),
                ),
                (
                    "subject",
                    models.CharField(blank=True, max_length=500, verbose_name="Asunto"),
                ),
                (
                    "sender",
                    models.CharField(blank=True, max_length=255, verbose_name="Remitente"),
                ),
                (
                    "date_sent",
                    models.DateTimeField(blank=True, null=True, verbose_name="Fecha del Correo"),
                ),
                (
                    "chunks_created",
                    models.PositiveIntegerField(default=0, verbose_name="Chunks Creados"),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("PROCESSED", "Procesado e Indexado"),
                            ("SKIPPED_NOISE", "Omitido (Ruido / Transaccional)"),
                            ("ERROR", "Error de Procesamiento"),
                        ],
                        default="PROCESSED",
                        max_length=30,
                        verbose_name="Estado",
                    ),
                ),
                (
                    "error_message",
                    models.TextField(blank=True, verbose_name="Mensaje de Error"),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "agencia",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="%(class)s_agencias",
                        to="core.agencia",
                        verbose_name="Agencia",
                    ),
                ),
            ],
            options={
                "verbose_name": "Registro de Correo Histórico RAG",
                "verbose_name_plural": "Registros de Correos Históricos RAG",
                "ordering": ["-created_at"],
            },
        ),
    ]

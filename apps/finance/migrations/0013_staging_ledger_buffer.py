import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0001_initial"),  # Depende de core para la Agencia y Usuario
        ("finance", "0012_remove_facturaconsolidada_agencia_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="PropuestaTransaccionIA",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                (
                    "accion_tipo",
                    models.CharField(
                        choices=[
                            ("CREAR_ASIENTO", "Crear Asiento Contable"),
                            ("CONCILIAR_REPORTE", "Conciliar Reporte de Proveedor"),
                        ],
                        max_length=50,
                    ),
                ),
                (
                    "payload_datos",
                    models.JSONField(
                        help_text="Datos estructurados necesarios para ejecutar la acción de forma determinista."
                    ),
                ),
                (
                    "justificacion",
                    models.TextField(
                        help_text="Explicación detallada de por qué la IA propone esta transacción."
                    ),
                ),
                (
                    "estado",
                    models.CharField(
                        choices=[
                            ("PENDIENTE", "Pendiente de Revisión"),
                            ("APROBADA", "Aprobada"),
                            ("RECHAZADA", "Rechazada"),
                        ],
                        default="PENDIENTE",
                        max_length=20,
                    ),
                ),
                ("fecha_creacion", models.DateTimeField(auto_now_add=True)),
                ("fecha_resolucion", models.DateTimeField(blank=True, null=True)),
                (
                    "comentarios_resolucion",
                    models.TextField(
                        blank=True,
                        help_text="Notas añadidas por el CFO humano al aprobar o rechazar.",
                        null=True,
                    ),
                ),
                (
                    "agencia",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="propuestas_ia",
                        to="core.agencia",
                    ),
                ),
                (
                    "usuario_resolutor",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="propuestas_ia_resueltas",
                        to="core.usuarioagencia",
                    ),
                ),
            ],
            options={
                "verbose_name": "Propuesta de Transacción IA",
                "verbose_name_plural": "Propuestas de Transacción IA",
                "ordering": ["-fecha_creacion"],
            },
        ),
        migrations.AddIndex(
            model_name="propuestatransaccionia",
            index=models.Index(fields=["agencia", "estado"], name="finance_pro_agencia_ea911b_idx"),
        ),
    ]

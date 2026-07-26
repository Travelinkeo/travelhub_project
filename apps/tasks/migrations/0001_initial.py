import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("core", "0056_agenciasetupprogress"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Tarea",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("titulo", models.CharField(max_length=200)),
                ("descripcion", models.TextField(blank=True)),
                (
                    "prioridad",
                    models.CharField(
                        choices=[
                            ("baja", "Baja"),
                            ("media", "Media"),
                            ("alta", "Alta"),
                            ("urgente", "Urgente"),
                        ],
                        default="media",
                        max_length=20,
                    ),
                ),
                (
                    "estado",
                    models.CharField(
                        choices=[
                            ("pendiente", "Pendiente"),
                            ("en_progreso", "En Progreso"),
                            ("revision", "En Revisión"),
                            ("completada", "Completada"),
                            ("cancelada", "Cancelada"),
                        ],
                        default="pendiente",
                        max_length=20,
                    ),
                ),
                ("fecha_vencimiento", models.DateField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
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
                (
                    "asignado_a",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="tareas_asignadas",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "creado_por",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="tareas_creadas",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Tarea",
                "verbose_name_plural": "Tareas",
                "ordering": ["-prioridad", "created_at"],
            },
        ),
        migrations.CreateModel(
            name="ComentarioTarea",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("texto", models.TextField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
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
                (
                    "tarea",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="comentarios",
                        to="tasks.tarea",
                    ),
                ),
                (
                    "usuario",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL
                    ),
                ),
            ],
            options={
                "verbose_name": "Comentario",
                "verbose_name_plural": "Comentarios",
                "ordering": ["created_at"],
            },
        ),
    ]

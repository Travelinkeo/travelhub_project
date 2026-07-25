"""Migración de base de datos para gamification.
"""

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration:
    """Clase Migration. Uso: según contexto de la aplicación.
    """
    initial = True

    dependencies = [
        ("core", "0056_agenciasetupprogress"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Logro",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                (
                    "codigo",
                    models.SlugField(
                        help_text="Código único del logro (ej: primera_venta)",
                        max_length=60,
                        unique=True,
                    ),
                ),
                ("nombre", models.CharField(max_length=120)),
                ("descripcion", models.TextField(blank=True)),
                (
                    "icono",
                    models.CharField(
                        default="emoji_events",
                        help_text="Material Symbol name",
                        max_length=60,
                    ),
                ),
                (
                    "categoria",
                    models.CharField(
                        choices=[
                            ("ventas", "Ventas"),
                            ("importacion", "Importación"),
                            ("clientes", "Clientes"),
                            ("contenido", "Contenido"),
                            ("configuracion", "Configuración"),
                            ("equipo", "Equipo"),
                            ("especial", "Especial"),
                        ],
                        default="especial",
                        max_length=30,
                    ),
                ),
                ("puntos", models.PositiveIntegerField(default=10)),
                ("activo", models.BooleanField(default=True)),
            ],
            options={
                "verbose_name": "Logro",
                "verbose_name_plural": "Logros",
            },
        ),
        migrations.CreateModel(
            name="Nivel",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("nombre", models.CharField(max_length=60)),
                ("icono", models.CharField(default="stars", max_length=100)),
                (
                    "color",
                    models.CharField(default="#6B7280", help_text="Hex color", max_length=7),
                ),
                ("puntos_minimos", models.PositiveIntegerField(unique=True)),
                ("descripcion", models.TextField(blank=True)),
            ],
            options={
                "verbose_name": "Nivel",
                "verbose_name_plural": "Niveles",
                "ordering": ["puntos_minimos"],
            },
        ),
        migrations.CreateModel(
            name="PuntuacionUsuario",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("puntos_total", models.PositiveIntegerField(default=0)),
                ("logros_completados", models.PositiveIntegerField(default=0)),
                ("ultima_actualizacion", models.DateTimeField(auto_now=True)),
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
                    "nivel",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="gamification.nivel",
                    ),
                ),
                (
                    "usuario",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="puntuacion",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Puntuación de Usuario",
                "verbose_name_plural": "Puntuaciones de Usuarios",
                "unique_together": {("usuario", "agencia")},
            },
        ),
        migrations.CreateModel(
            name="LogroProgreso",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("progreso", models.PositiveIntegerField(default=0, help_text="Progreso actual (0-100)")),
                ("completado", models.BooleanField(default=False)),
                ("fecha_completado", models.DateTimeField(blank=True, null=True)),
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
                    "logro",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="progresos",
                        to="gamification.logro",
                    ),
                ),
                (
                    "usuario",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="logros",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Progreso de Logro",
                "verbose_name_plural": "Progresos de Logros",
                "ordering": ["-completado", "-progreso"],
                "unique_together": {("usuario", "logro", "agencia")},
            },
        ),
    ]

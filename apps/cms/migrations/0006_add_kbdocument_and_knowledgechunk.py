import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("cms", "0004_alter_articulo_agencia_alter_guiadestino_agencia_and_more"),
        ("core", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="KBDocument",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("title", models.CharField(max_length=255, verbose_name="Título del Documento")),
                (
                    "gds_type",
                    models.CharField(
                        choices=[
                            ("SABRE", "Sabre GDS"),
                            ("AMADEUS", "Amadeus GDS"),
                            ("KIU", "KIU System"),
                            ("TRAVELPORT", "Travelport / Galileo"),
                            ("GENERAL", "General / Operaciones"),
                        ],
                        default="GENERAL",
                        max_length=30,
                        verbose_name="Tipo / GDS",
                    ),
                ),
                (
                    "archivo_pdf",
                    models.FileField(upload_to="kb_documents/", verbose_name="Archivo PDF"),
                ),
                ("descripcion", models.TextField(blank=True, verbose_name="Descripción / Notas")),
                (
                    "is_indexed",
                    models.BooleanField(default=False, verbose_name="Indexado en Vector RAG"),
                ),
                ("indexed_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "agencia",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to="core.agencia",
                    ),
                ),
            ],
            options={
                "verbose_name": "Documento KB / Manual",
                "verbose_name_plural": "Documentos KB / Manuales",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="KnowledgeChunk",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                (
                    "source_type",
                    models.CharField(
                        choices=[
                            ("WIKI", "Artículo de Wiki / KB"),
                            ("MANUAL_GDS", "Manual PDF / GDS"),
                            ("MAILBOT", "Correo Informativo / Mailbot"),
                        ],
                        max_length=30,
                        verbose_name="Tipo de Fuente",
                    ),
                ),
                ("source_title", models.CharField(max_length=255, verbose_name="Título de Fuente")),
                (
                    "source_reference_id",
                    models.CharField(
                        blank=True, max_length=255, verbose_name="Referencia ID / Archivo"
                    ),
                ),
                ("content_chunk", models.TextField(verbose_name="Fragmento de Texto")),
                (
                    "embedding_vector",
                    models.JSONField(blank=True, default=list, verbose_name="Vector Embedding"),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "agencia",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to="core.agencia",
                    ),
                ),
            ],
            options={
                "verbose_name": "Fragmento Vectorial RAG",
                "verbose_name_plural": "Fragmentos Vectoriales RAG",
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(fields=["source_type"], name="cms_knowled_source__3d92ff_idx")
                ],
            },
        ),
    ]

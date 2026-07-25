"""Migración de base de datos para bookings.
"""

from django.db import migrations, models


class Migration:
    """Clase Migration. Uso: según contexto de la aplicación.
    """
    dependencies = [
        ("bookings", "0039_add_hoteltarifario_amenidades_m2m"),
    ]

    operations = [
        migrations.AlterField(
            model_name="feeventa",
            name="creado",
            field=models.DateTimeField(auto_now_add=True, db_index=True),
        ),
        migrations.AlterField(
            model_name="venta",
            name="localizador",
            field=models.CharField(
                blank=True,
                db_index=True,
                help_text="Código único de la reserva o localizador.",
                max_length=20,
                verbose_name="Localizador/PNR",
            ),
        ),
        migrations.AddIndex(
            model_name="ventaauditfinding",
            index=models.Index(
                fields=["venta", "estado", "fecha_deteccion"], name="idx_audit_venta_estado_fecha"
            ),
        ),
    ]

"""Migración de base de datos para finance.
"""

from django.db import migrations, models


class Migration:
    """Clase Migration. Uso: según contexto de la aplicación.
    """
    dependencies = [
        ("finance", "0025_add_missing_agencia_columns"),
    ]

    operations = [
        migrations.AlterField(
            model_name="pago",
            name="creado",
            field=models.DateTimeField(auto_now_add=True, db_index=True),
        ),
        migrations.AddIndex(
            model_name="facturafiscal",
            index=models.Index(
                fields=["venta", "estado_fiscal"], name="idx_facturafiscal_venta_estado"
            ),
        ),
    ]

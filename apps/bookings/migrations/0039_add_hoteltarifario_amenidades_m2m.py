"""Migración de base de datos para bookings.
"""

from django.db import migrations, models


class Migration:
    """Clase Migration. Uso: según contexto de la aplicación.
    """
    dependencies = [
        ("bookings", "0038_add_missing_fk_and_softdelete_columns"),
    ]

    operations = [
        migrations.AddField(
            model_name="hoteltarifario",
            name="amenidades",
            field=models.ManyToManyField(
                blank=True,
                related_name="hoteles",
                to="bookings.amenity",
            ),
        ),
    ]

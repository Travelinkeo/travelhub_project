"""Migración de base de datos para bookings.
"""

import django.db.models.deletion
from django.db import migrations, models


class Migration:
    """Clase Migration. Uso: según contexto de la aplicación.
    """
    dependencies = [
        ("bookings", "0037_tarifarioproveedor_add_agencia_proveedor"),
        ("common", "0004_alter_aerolinea_table_alter_ciudad_table_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="comisionoverrideaerolinea",
            name="aerolinea",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                to="common.aerolinea",
                verbose_name="Aerol\u00ednea",
            ),
        ),
        migrations.AddField(
            model_name="comisionoverrideaerolinea",
            name="tarifario",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="overrides_aerolinea",
                to="bookings.tarifarioproveedor",
            ),
        ),
        migrations.AddField(
            model_name="hoteltarifario",
            name="agencia",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="+",
                to="core.agencia",
            ),
        ),
        migrations.AddField(
            model_name="hoteltarifario",
            name="tarifario",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="hoteles",
                to="bookings.tarifarioproveedor",
            ),
        ),
        migrations.AddField(
            model_name="tipohabitacion",
            name="hotel",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="habitaciones",
                to="bookings.hoteltarifario",
            ),
        ),
        migrations.AddField(
            model_name="tarifahabitacion",
            name="tipo_habitacion",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="tarifas",
                to="bookings.tipohabitacion",
            ),
        ),
        migrations.AddField(
            model_name="imagenhotel",
            name="hotel",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="imagenes",
                to="bookings.hoteltarifario",
            ),
        ),
        migrations.AddField(
            model_name="productoterrestre",
            name="agencia",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="+",
                to="core.agencia",
            ),
        ),
        migrations.AddField(
            model_name="productoterrestre",
            name="deleted_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="productoterrestre",
            name="is_deleted",
            field=models.BooleanField(default=False),
        ),
    ]

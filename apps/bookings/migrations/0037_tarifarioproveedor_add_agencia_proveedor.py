import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("bookings", "0036_rename_core_tables_to_bookings"),
    ]

    operations = [
        migrations.AddField(
            model_name="tarifarioproveedor",
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
            model_name="tarifarioproveedor",
            name="proveedor",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="tarifarios",
                to="bookings.proveedor",
            ),
        ),
    ]

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("bookings", "0048_secuenciaventadiaria"),
        ("core", "0053_ssoprovider"),
    ]

    operations = [
        migrations.AddField(
            model_name="tarifahabitacion",
            name="agencia",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="%(class)s_items",
                to="core.agencia",
                verbose_name="Agencia",
            ),
        ),
    ]

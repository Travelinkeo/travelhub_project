# Generated migration for es_reemision on BoletoImportado

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("bookings", "0049_tarifahabitacion_agencia"),
    ]

    operations = [
        migrations.AddField(
            model_name="boletoimportado",
            name="es_reemision",
            field=models.BooleanField(
                default=False,
                help_text="Indica si este boleto es una reemisión o remisión posterior a una factura emitida.",
                verbose_name="Es Reemisión / Exchange",
            ),
        ),
    ]

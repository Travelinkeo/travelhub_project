# Generated migration for bimoneda fields on ItemFactura

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("finance", "0037_fiscal_tsj256_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="itemfactura",
            name="precio_unitario_ves",
            field=models.DecimalField(blank=True, decimal_places=4, max_digits=15, null=True),
        ),
        migrations.AddField(
            model_name="itemfactura",
            name="total_linea_ves",
            field=models.DecimalField(blank=True, decimal_places=4, max_digits=15, null=True),
        ),
    ]
